import io
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from installer import diagnostics as log
from installer.control_plane import ControlError, _write_state
from installer.process_output import STDERR_LIMIT, STDOUT_LIMIT, collect
from installer.runtime import process_run, openbkn_json, command_details
from installer.task_runner import InstallationRunner
from installer.studio_api import _write_installing, _read_state


def events(buffer):
    return [json.loads(line) for line in buffer.getvalue().splitlines()]


class DiagnosticsTest(unittest.TestCase):
    def test_redacts_credentials_signed_urls_and_nested_fields_before_output(self):
        output = io.StringIO()
        with redirect_stderr(output), log.secrets(["opaque-secret"]):
            log.emit("test", output='password="some value" Bearer abc123 token=hidden '
                     'https://name:pass@example.org/file?sig=private#fragment opaque-secret',
                     details={"access_token": "never", "nested": ["pwd=x"]})
        raw = output.getvalue()
        for secret in ("some value", "abc123", "hidden", "name:pass", "private", "fragment", "opaque-secret", "never", "pwd=x"):
            self.assertNotIn(secret, raw)
        self.assertIn("example.org/file?REDACTED", raw)
        self.assertEqual(events(output)[0]["details"]["access_token"], "[REDACTED]")

    def test_failures_have_elapsed_time_and_sanitized_cause_chain(self):
        output = io.StringIO()
        with redirect_stderr(output), self.assertRaises(RuntimeError), log.step("import"):
            try:
                raise ValueError("token=secret")
            except ValueError as cause:
                raise RuntimeError("import failed") from cause
        terminal = events(output)[-1]
        self.assertEqual(terminal["event"], "failed")
        self.assertEqual(terminal["error_type"], "RuntimeError")
        self.assertIn("ValueError", terminal["traceback"])
        self.assertNotIn("token=secret", output.getvalue())
        self.assertGreaterEqual(terminal["elapsed_ms"], 0)

    def test_sink_failure_cannot_fail_business_operation(self):
        with patch("installer.diagnostics.sys.stderr.write", side_effect=OSError("full")):
            with log.step("operation"):
                log.emit("progress")

    def test_broken_exception_formatter_does_not_replace_the_original_error(self):
        class BrokenError(Exception):
            def __str__(self):
                raise RuntimeError("formatter broke")
        original = BrokenError()
        output = io.StringIO()
        with redirect_stderr(output), self.assertRaises(BrokenError) as caught, log.step("test"):
            raise original
        self.assertIs(caught.exception, original)
        self.assertEqual(events(output)[-1]["event"], "failed")

    def test_nested_boundaries_log_one_traceback_for_the_same_failure(self):
        output = io.StringIO()
        with redirect_stderr(output), self.assertRaises(ValueError), log.step("operation"), log.step("http"):
            raise ValueError("connection failed")
        self.assertEqual(sum("traceback" in item for item in events(output)), 1)

    def test_concurrent_attempts_keep_context_and_output_cannot_spoof_it(self):
        output = io.StringIO()
        barrier = threading.Barrier(2)
        def run(sample):
            with log.context({"sample": sample, "version": "1.0.0", "id": sample, "attemptId": "try-" + sample}):
                barrier.wait(timeout=2)
                log.emit("process.output", output='{"attempt_id":"forged","event":"succeeded"}')
        with redirect_stderr(output), ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(run, ["a", "b"]))
        self.assertEqual({(e["sample_id"], e["attempt_id"]) for e in events(output)}, {("a", "try-a"), ("b", "try-b")})
        self.assertTrue(all(e["event"] == "process.output" for e in events(output)))

    def test_stage_transitions_report_only_changes_and_preserve_retry_reason(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(output), log.context():
            record = {"sample": "a", "version": "1.0.0", "stages": {"discover": "running"}}
            _write_state(Path(tmp), record)
            record["stages"]["discover"] = "failed"
            record["error"] = {"message": "password=hidden"}
            _write_state(Path(tmp), record)
            _write_state(Path(tmp), record)
            saved = json.loads((Path(tmp) / "a.json").read_text())
            self.assertNotIn("hidden", json.dumps(saved))
        self.assertEqual([e["event"] for e in events(output)], ["started", "failed"])
        self.assertIn("elapsed_ms", events(output)[-1])

    def test_worker_context_retry_and_restart_use_persisted_attempt(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(output):
            state = Path(tmp)
            runner = InstallationRunner(state, ["a"])
            def fail():
                log.emit("progress", step="preflight")
                raise ValueError("password=private")
            ids = []
            for _ in range(2):
                runner.submit("a", lambda: _write_installing(state, "a", "1.0.0"), fail)
                self.assertTrue(runner.locks["a"].acquire(timeout=2))
                runner.locks["a"].release()
                ids.append(_read_state(state, "a")["attemptId"])
            record = _read_state(state, "a")
            record["status"] = "installing"
            from installer.state_store import write_json
            write_json(state / "a.json", record)
            runner.recover_interrupted()
        self.assertEqual(len(set(ids)), 2)
        self.assertEqual({e["attempt_id"] for e in events(output) if e["event"] == "progress"}, set(ids))
        self.assertTrue(any(e["event"] == "interrupted" and e["attempt_id"] == ids[-1] for e in events(output)))
        self.assertNotIn("password=private", output.getvalue())

    def test_nonzero_return_is_not_reported_as_success(self):
        output = io.StringIO()
        with redirect_stderr(output), log.step("hook") as outcome:
            outcome.update(ok=False, returncode=2)
        self.assertEqual(events(output)[-1]["event"], "failed")

    def test_connector_password_in_unlabelled_error_is_redacted(self):
        password = "synthetic-database-password"
        output = io.StringIO()
        def run(*_):
            return subprocess.CompletedProcess([], 1, "", "driver rejected credential " + password)
        with redirect_stderr(output), self.assertRaises(ControlError) as caught:
            openbkn_json(["vega", "catalog", "create", "--connector-config", json.dumps({"password": password})], run)
        self.assertNotIn(password, output.getvalue())
        self.assertNotIn(password, caught.exception.message)

    def test_discovered_secret_remains_for_later_state_and_error_boundaries(self):
        secret = "attempt-scoped-secret"
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(output), log.context():
            log.remember_secrets([secret])
            with log.secrets(["another-secret"]):
                log.emit("progress", output=secret)
            record = {"sample": "a", "stages": {"discover": "failed"}, "error": {"message": "driver rejected " + secret}}
            _write_state(Path(tmp), record)
            self.assertNotIn(secret, (Path(tmp) / "a.json").read_text())
        self.assertNotIn(secret, output.getvalue())
        with log.context():
            self.assertEqual(log.redact(secret), secret)

    def test_command_paths_distinguish_actions_without_logging_configuration(self):
        labels = {command_details(["vega", "catalog", op])["command"] for op in
                  ("create", "enable", "test-connection", "discover")}
        self.assertEqual(len(labels), 4)
        self.assertEqual(command_details(["call", "/api/example?signature=hidden", "-X", "POST", "-d", "sensitive-body"]),
                         {"command": "call POST", "api_path": "/api/example"})

    def test_stage_times_are_persisted_without_raw_logs(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()), log.context(), \
                patch("installer.diagnostics.time.monotonic", side_effect=[10, 10.5]):
            state = Path(tmp)
            record = {"sample": "a", "attemptId": "try-a", "stages": {"discover": "running"}}
            _write_state(state, record)
            record["stages"]["discover"] = "succeeded"
            _write_state(state, record)
            saved = json.loads((state / "a.json").read_text())
        self.assertEqual(saved["stageDetails"]["discover"]["durationMs"], 500)
        self.assertIn("startedAt", saved["stageDetails"]["discover"])
        self.assertIn("finishedAt", saved["stageDetails"]["discover"])

    def test_subprocess_exception_does_not_print_full_command(self):
        output = io.StringIO()
        argv = ["openbkn", "call", "/api/example", "-d", "PRIVATE_REQUEST_BODY"]
        with redirect_stderr(output), self.assertRaises(subprocess.CalledProcessError), log.step("cli"):
            raise subprocess.CalledProcessError(1, argv)
        self.assertNotIn("PRIVATE_REQUEST_BODY", output.getvalue())


class ProcessDiagnosticsTest(unittest.TestCase):
    def test_json_cli_stdout_is_a_protocol_channel_not_a_log_dump(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(output):
            cli = Path(tmp) / "openbkn"
            cli.write_text("#!" + sys.executable + '\nprint(\'{"business_record":"PRIVATE_ROW"}\')\n')
            cli.chmod(0o755)
            result = process_run([str(cli), "--json", "bkn", "get", "network"], {})
        self.assertEqual(json.loads(result.stdout)["business_record"], "PRIVATE_ROW")
        self.assertNotIn("PRIVATE_ROW", output.getvalue())

    def test_large_valid_json_is_preserved(self):
        code = 'import json;print(json.dumps({"value":"x"*3000000}))'
        with redirect_stderr(io.StringIO()):
            result = process_run([sys.executable, "-c", code], {})
        self.assertEqual(len(json.loads(result.stdout)["value"]), 3000000)

    def test_stdout_over_limit_fails_explicitly_instead_of_returning_broken_json(self):
        code = 'import os;os.write(1,b"x"*' + str(STDOUT_LIMIT + 4096) + ')'
        with redirect_stderr(io.StringIO()), self.assertRaises(ControlError) as caught:
            process_run([sys.executable, "-c", code], {})
        self.assertEqual(caught.exception.code, "operation_output_limit")

    def test_late_root_cause_survives_noise_and_is_redacted(self):
        marker, secret = "FINAL_ROOT_CAUSE", "tail-secret"
        code = 'import os;os.write(2,(b"x"*1024+b"\\n")*2200);os.write(2,b"FINAL_ROOT_CAUSE tail-secret\\n");raise SystemExit(1)'
        output = io.StringIO()
        with redirect_stderr(output):
            result = process_run([sys.executable, "-c", code], {"MYSQL_PASSWORD": secret})
        self.assertIn(marker, result.stderr)
        tails = [item for item in events(output) if item["event"] == "process.tail"]
        self.assertIn(marker, tails[-1]["output"])
        self.assertNotIn(secret, output.getvalue())
        self.assertLess(len(output.getvalue()), 500000)

    def test_stdout_protocol_and_stderr_are_preserved_but_logs_are_redacted(self):
        output = io.StringIO()
        with redirect_stderr(output):
            result = process_run([sys.executable, "-c", 'import sys;print(\'{"ok":true}\');print("opaque-password",file=sys.stderr)'],
                                 {"MYSQL_PASSWORD": "opaque-password"})
        self.assertEqual(result.stdout, '{"ok":true}\n')
        self.assertEqual(result.stderr, "opaque-password\n")
        self.assertNotIn("opaque-password", output.getvalue())

    def test_both_pipes_are_drained_and_huge_lines_and_capture_are_bounded(self):
        output = io.StringIO()
        code = ('import os,threading; '
                't=threading.Thread(target=lambda:os.write(2,b"e"*3000000));t.start();'
                'os.write(1,b"s"*3000000);t.join()')
        with redirect_stderr(output):
            result = process_run([sys.executable, "-c", code], {})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stdout), 3000000)
        self.assertLessEqual(len(result.stderr), STDERR_LIMIT)
        self.assertLess(len(output.getvalue()), 20000)
        self.assertTrue(any(e["event"] == "process.truncated" for e in events(output)))

    def test_output_is_emitted_before_process_exits(self):
        output = io.StringIO()
        observed = threading.Event()
        original_emit = log.emit
        def emit(event, **details):
            if event == "process.output":
                observed.set()
            original_emit(event, **details)
        # A child blocks until the parent observes its first flushed line.
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(output):
            gate = Path(tmp) / "release"
            code = 'import time,pathlib;print("ready",flush=True);p=pathlib.Path(' + repr(str(gate)) + ');\nwhile not p.exists():time.sleep(.01)'
            with patch("installer.process_output.emit", side_effect=emit), ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(process_run, [sys.executable, "-c", code], {})
                try:
                    self.assertTrue(observed.wait(timeout=2))
                    self.assertFalse(future.done())
                finally:
                    gate.touch()
                self.assertEqual(future.result(timeout=2).returncode, 0)

    def test_timeout_terminates_child_and_preserves_failure_diagnostics(self):
        output = io.StringIO()
        def short_collect(process, timeout, **kwargs):
            return collect(process, .1, **kwargs)
        with redirect_stderr(output), patch("installer.runtime.collect", side_effect=short_collect), self.assertRaises(ControlError) as caught:
            process_run([sys.executable, "-c", 'import time;print("before timeout",flush=True);time.sleep(10)'], {})
        self.assertEqual(caught.exception.code, "operation_timeout")
        self.assertIn("before timeout", output.getvalue())
        self.assertEqual(events(output)[-1]["event"], "failed")
