"""Bounded, best-effort JSON diagnostics on stderr; never part of the hook protocol."""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
import json
import re
import sys
import subprocess
import time
import traceback
from urllib.parse import urlsplit, urlunsplit

_context = ContextVar("sample_diagnostics", default={})
_secrets = ContextVar("sample_secrets", default=None)
_timers = ContextVar("sample_stage_timers", default=None)
MAX_TEXT = 4096
_SENSITIVE = re.compile(r"(?i)(password|passwd|pwd|token|authorization|secret|credential|api[_-]?key|signature)")
_ASSIGNMENT = re.compile(
    r'''(?ix)(["']?(?:password|passwd|pwd|(?:access_|refresh_)?token|authorization|secret|api[_-]?key|signature)["']?\s*[:=]\s*)
    ("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\s,;}]+)''')
_BEARER = re.compile(r"(?i)\bBearer\s+[^\s\"',;}]+")
_URL = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s<>\"']+")


def safe_url(value):
    """Keep the diagnostic target, never URL credentials, query values or fragments."""
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if ":" in host:
            host = "[" + host + "]"
        if parsed.port:
            host += ":" + str(parsed.port)
        return urlunsplit((parsed.scheme, host, parsed.path, "REDACTED" if parsed.query else "", ""))
    except ValueError:
        return "[invalid URL]"


def redact(value, *, limit=MAX_TEXT):
    text = str(value)
    for secret in sorted(_secrets.get() or (), key=len, reverse=True):
        text = text.replace(secret, "[REDACTED]")
    text = _URL.sub(lambda match: safe_url(match.group()), text)
    text = _BEARER.sub("Bearer [REDACTED]", text)
    text = _ASSIGNMENT.sub(lambda match: match[1] + '"[REDACTED]"', text)
    return text if limit is None else text[:limit] + (" [truncated]" if len(text) > limit else "")


def _clean(value):
    if isinstance(value, dict):
        return {str(k): "[REDACTED]" if _SENSITIVE.search(str(k)) else _clean(v)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value[:30]]
    return redact(value) if isinstance(value, str) else value


@contextmanager
def context(record=None, **fields):
    inherited = _context.get()
    if record:
        fields = {**fields, "sample_id": record.get("sample"), "version": record.get("version"),
                  "installation_id": record.get("id"), "attempt_id": record.get("attemptId"),
                  "operation": record.get("operation", "install")}
    token = _context.set({**inherited, **fields})
    secret_token = _secrets.set(set()) if _secrets.get() is None else None
    timer = _timers.set({}) if _timers.get() is None else None
    try:
        yield
    finally:
        _context.reset(token)
        if secret_token is not None:
            _secrets.reset(secret_token)
        if timer is not None:
            _timers.reset(timer)


@contextmanager
def secrets(values):
    token = _secrets.set(set(_secrets.get() or ()))
    remember_secrets(values)
    try:
        yield
    finally:
        _secrets.reset(token)


def remember_secrets(values):
    """Keep known values until the enclosing operation finishes, never globally."""
    registry = _secrets.get()
    if registry is not None:
        for value in values:
            if value:
                text = str(value)
                registry.update([text, json.dumps(text, ensure_ascii=False)[1:-1]])
                registry.update(part for part in text.splitlines() if part)


def sensitive_values(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if _SENSITIVE.search(str(key)) and isinstance(item, str):
                yield item
            else:
                yield from sensitive_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from sensitive_values(item)


def operation_context(function):
    """Also scope direct library calls; worker calls retain their attempt context."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        with context(sample_id=kwargs.get("sample"), version=kwargs.get("version")):
            authorization = kwargs.get("authorization") or ""
            remember_secrets([authorization, authorization.removeprefix("Bearer ")])
            return function(*args, **kwargs)
    return wrapped


def command_details(args):
    if args and args[0] == "call":
        method = args[args.index("-X") + 1] if "-X" in args and args.index("-X") + 1 < len(args) else "GET"
        path = next((item for item in args[1:] if item.startswith("/api/")), "")
        return {"command": "call " + (method if method in {"GET", "POST", "PUT", "DELETE", "PATCH"} else "unknown"),
                "api_path": path.split("?", 1)[0]}
    depth = 3 if len(args) > 2 and (args[:2] == ["vega", "catalog"] or
            args[0] == "bkn" and args[1] in {"object-type", "relation-type", "capability", "object-metric"}) else 2
    details = {"command": " ".join(args[:depth])}
    if len(args) > depth and re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", args[depth]):
        details["resource_id"] = args[depth]
    if args[:2] == ["bkn", "object-type"] and len(args) > 4 and re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", args[4]):
        details["object_type_id"] = args[4]
    return details


def hook_context():
    return json.dumps({key: value for key, value in _context.get().items()
                       if key in {"sample_id", "version", "installation_id", "attempt_id", "operation"}})


def command_failure(completed):
    """Prefer the failure tail; only recognized error fields may leave JSON stdout."""
    if completed.stderr:
        return redact(completed.stderr, limit=None).strip()[-MAX_TEXT:]
    try:
        payload = json.loads(completed.stdout or "{}")
    except (ValueError, TypeError):
        return "Command failed"
    if isinstance(payload, dict):
        details = {key: payload[key] for key in ("error_code", "code", "description", "message", "error_details")
                   if isinstance(payload.get(key), str)}
        if details:
            return redact(json.dumps(details, ensure_ascii=False))
    return "Command failed"


def emit(event, *, level="info", **details):
    """Diagnostic sink failures must not change installation results."""
    try:
        body = {"time": datetime.now(timezone.utc).isoformat(), "level": level,
                "sample_id": None, "version": None, "installation_id": None,
                "attempt_id": None, "operation": "install", "stage": None, "step": None,
                **_context.get(), **details, "event": event}
        # Output is always text, never parsed as trusted event/context fields.
        sys.stderr.write(json.dumps(_clean(body), ensure_ascii=False) + "\n")
        sys.stderr.flush()
    except Exception:
        pass


def record_failure(error, **fields):
    """Report caught failures too; exclude argv, source snippets and locals."""
    details = {}
    try:
        def reason(exc):
            if isinstance(exc, subprocess.TimeoutExpired):
                return "Command timed out"
            if isinstance(exc, subprocess.CalledProcessError):
                return "Command exited with status " + str(exc.returncode)
            return str(exc)
        message = reason(error)
        if not getattr(error, "_sample_diagnostic_logged", False):
            chain, seen, node = [], set(), error
            while node is not None and id(node) not in seen and len(chain) < 8:
                seen.add(id(node))
                frames = [f"  {frame.filename}:{frame.lineno} in {frame.name}" for frame in traceback.extract_tb(node.__traceback__)]
                chain.append("\n".join([*frames, type(node).__name__ + ": " + reason(node)]))
                node = node.__cause__ or (None if node.__suppress_context__ else node.__context__)
            details["traceback"] = redact("\nCaused by:\n".join(chain))
            error._sample_diagnostic_logged = True
        code = getattr(error, "code", None)
        if isinstance(code, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,159}", code):
            details["error_code"] = code
        elif type(code) is int and 100 <= code <= 599:
            details["http_status"] = code
    except Exception:
        message = "Exception details unavailable"
    emit("interrupted" if isinstance(error, (KeyboardInterrupt, SystemExit)) else "failed",
         level="error", error_type=type(error).__name__, reason=message, **details, **fields)


@contextmanager
def step(name, **details):
    start = time.monotonic()
    result = {}
    with context(step=name):
        emit("started", **details)
        try:
            yield result
        except BaseException as error:
            record_failure(error, elapsed_ms=round((time.monotonic() - start) * 1000))
            raise
        else:
            failed = result.get("ok") is False
            result["elapsed_ms"] = round((time.monotonic() - start) * 1000)
            emit("failed" if failed else "succeeded", level="error" if failed else "info",
                 **result)


def stage_changes(previous, current):
    """Prepare small stage receipts before persistence; raw output stays in logs."""
    timers = _timers.get()
    events = []
    for stage, state in current.get("stages", {}).items():
        old = (previous or {}).get("stages", {}).get(stage)
        same_attempt = current.get("stageDetails", {}).get(stage, {}).get("attemptId") == current.get("attemptId")
        if old == state and (state != "running" or same_attempt):
            continue
        receipt = current.setdefault("stageDetails", {}).setdefault(stage, {})
        now = datetime.now(timezone.utc).isoformat()
        details = {}
        if state == "running":
            receipt.clear()
            receipt.update(startedAt=now, attemptId=current.get("attemptId"))
            if timers is not None:
                timers[stage] = time.monotonic()
        else:
            receipt["finishedAt"] = now
            if timers is not None and stage in timers:
                details["elapsed_ms"] = round((time.monotonic() - timers.pop(stage)) * 1000)
                receipt["durationMs"] = details["elapsed_ms"]
        receipt["state"] = state
        if state == "failed":
            details["reason"] = redact(current.get("error", {}).get("message", "Stage failed"))
            receipt["reason"] = details["reason"]
        events.append({"event": "started" if state == "running" else state, "stage": stage,
                       "step": stage, "level": "error" if state == "failed" else "info", **details})
    return events


def transitions(previous, current, *, changes=None):
    """Emit after the associated receipt has been persisted."""
    with context(current):
        for change in stage_changes(previous, current) if changes is None else changes:
            emit(**change)
