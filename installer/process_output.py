"""Drain both pipes without truncating protocol JSON or losing failure tails."""

import os
import json
import re
import selectors
import subprocess
import time

from installer.diagnostics import emit, MAX_TEXT

STDOUT_LIMIT = 16 * 1024 * 1024
STDERR_LIMIT = 64 * 1024
LINE_LIMIT = 8192
LOG_LIMIT = 256 * 1024
LOG_EVENT_LIMIT = 256


def _sample_event(data):
    """Only diagnostic fields are accepted; identity always comes from the parent."""
    try:
        event = json.loads(data)
    except (ValueError, UnicodeError):
        return False
    if not isinstance(event, dict) or event.get("source") != "sample":
        return False
    name = event.get("event")
    step = event.get("step")
    if name not in {"started", "succeeded", "failed", "skipped", "progress", "interrupted"} or not isinstance(step, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", step):
        return False
    details = {key: event[key] for key in ("command", "resource_id", "object_type_id", "api_path", "reason", "traceback")
               if isinstance(event.get(key), str)}
    for key in ("elapsed_ms", "returncode"):
        if type(event.get(key)) is int:
            details[key] = event[key]
    if event.get("stage") in {"database", "discover", "knowledge", "capabilities", "verify", "platform-install"}:
        details["child_stage"] = event["stage"]
    emit(name, source="sample", step="sample." + step,
         level="error" if name in {"failed", "interrupted"} else "info", **details)
    return True


class OutputLimitExceeded(Exception):
    pass


def _complete_tail(data, truncated):
    # A suffix may begin inside a secret. Only expose complete lines after
    # that boundary, even if this means omitting one overlong line entirely.
    if truncated:
        _, separator, data = data.partition(b"\n")
        if not separator:
            return b""
    return data


def collect(process, timeout, *, log_stdout=True):
    deadline = time.monotonic() + timeout
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    lines = {name: bytearray() for name in captured}
    dropping = {name: False for name in captured}
    truncated = set()
    logged_bytes = logged_events = 0

    def output(stream, data):
        nonlocal logged_bytes, logged_events
        if stream == "stdout" and not log_stdout:
            return
        if logged_bytes < LOG_LIMIT and logged_events < LOG_EVENT_LIMIT:
            logged_bytes += len(data)
            logged_events += 1
            if stream != "stderr" or not _sample_event(data):
                emit("process.output", stream=stream, output=data.decode("utf-8", errors="replace"))
        elif "log" not in truncated:
            truncated.add("log")
            emit("process.truncated", reason="output log limit", limit=LOG_LIMIT,
                 event_limit=LOG_EVENT_LIMIT)

    try:
        with selectors.DefaultSelector() as selector:
            for name in captured:
                pipe = getattr(process, name)
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, name)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(process.args, timeout)
                for key, _ in selector.select(min(remaining, 0.25)):
                    stream = key.data
                    block = os.read(key.fd, 4096)
                    if not block:
                        selector.unregister(key.fileobj)
                        if lines[stream] and not dropping[stream]:
                            output(stream, lines[stream])
                        continue
                    captured[stream].extend(block)
                    if stream == "stdout" and len(captured[stream]) > STDOUT_LIMIT:
                        raise OutputLimitExceeded("Command stdout exceeded the 16 MiB protocol limit.")
                    if stream == "stderr" and len(captured[stream]) > STDERR_LIMIT:
                        del captured[stream][:-STDERR_LIMIT]
                        if stream not in truncated:
                            truncated.add(stream)
                            emit("process.truncated", stream=stream, reason="capture tail limit", limit=STDERR_LIMIT)
                    if stream == "stdout" and not log_stdout:
                        continue
                    for part in block.splitlines(keepends=True):
                        if not dropping[stream]:
                            lines[stream].extend(part)
                            if len(lines[stream]) > LINE_LIMIT:
                                lines[stream].clear()
                                dropping[stream] = True
                                if stream + ".line" not in truncated:
                                    truncated.add(stream + ".line")
                                    emit("process.truncated", stream=stream, reason="line limit", limit=LINE_LIMIT)
                        if part.endswith((b"\n", b"\r")):
                            if not dropping[stream]:
                                output(stream, lines[stream])
                            lines[stream].clear()
                            dropping[stream] = False
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(process.args, timeout)
            process.wait(timeout=remaining)
    finally:
        if process.returncode != 0 and captured["stderr"]:
            tail = bytes(captured["stderr"])
            tail = _complete_tail(tail[-MAX_TEXT:], len(tail) > MAX_TEXT or "stderr" in truncated)
            if tail:
                emit("process.tail", level="error", stream="stderr",
                     output=tail.decode("utf-8", errors="replace"))
    stderr = _complete_tail(bytes(captured["stderr"]), "stderr" in truncated)
    return captured["stdout"].decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")
