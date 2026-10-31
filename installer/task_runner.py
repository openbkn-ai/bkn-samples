"""One worker per bundled sample, with state persisted before HTTP acceptance."""

from pathlib import Path
import re
from threading import Lock, Thread

from installer.state_store import write_json
from installer.history import begin_installation_attempt, record_terminal_installation
from installer.studio_api import ApiError, _read_state, installation_view, timestamp
from installer import diagnostics


class InstallationRunner:
    def __init__(self, state_dir: Path, samples):
        self.state_dir = state_dir
        self.locks = {sample: Lock() for sample in samples}
        self.registry_lock = Lock()

    def register(self, sample):
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", sample):
            raise ApiError(404, "install_failed", "unknown sample")
        with self.registry_lock:
            self.locks.setdefault(sample, Lock())

    def recover_interrupted(self):
        # A single Recreate replica owns this state directory. Never auto-replay writes.
        for path in self.state_dir.glob("*.json"):
            if re.fullmatch(r"[a-z][a-z0-9-]{0,31}", path.stem):
                current = _read_state(self.state_dir, path.stem)
                if isinstance(current, dict) and current.get("sample") == path.stem:
                    self.register(path.stem)
        for sample in self.locks:
            self._fail(sample, "install_interrupted", "Installation was interrupted; an administrator can retry.")

    def _fail(self, sample, code, message):
        current = _read_state(self.state_dir, sample)
        if not current or current.get("status") not in {"installing", "uninstalling"}:
            return
        previous = {**current, "stages": dict(current.get("stages", {}))}
        if current.get("operation") == "uninstall":
            code = "uninstall_interrupted" if code == "install_interrupted" else "uninstall_failed"
            message = "Uninstall was interrupted; an administrator can continue cleanup."
        current["status"] = "uninstall_failed" if current.get("operation") == "uninstall" else "failed"
        current["error"] = {"code": code, "message": message}
        current["finishedAt"] = timestamp()
        stages = current.setdefault("stages", {})
        for stage, status in list(stages.items()):
            if status == "running":
                stages[stage] = "failed"
        if not stages:
            stages["knowledge" if current.get("operation") == "uninstall" else "database"] = "failed"
        changes = diagnostics.stage_changes(previous, current)
        write_json(self.state_dir / f"{sample}.json", current)
        with diagnostics.context(current):
            diagnostics.transitions(previous, current, changes=changes)
            diagnostics.emit("interrupted" if code.endswith("interrupted") else "failed",
                             level="error", reason=message)
        record_terminal_installation(self.state_dir, current)

    def submit(self, sample, prepare, execute):
        lock = self.locks.get(sample)
        if lock is None:
            raise ApiError(404, "install_failed", "unknown sample")
        if not lock.acquire(blocking=False):
            raise ApiError(409, "already_installing", "an installation is already running")
        try:
            previous = _read_state(self.state_dir, sample)
            with diagnostics.context(sample_id=sample, version=(previous or {}).get("version"),
                                     operation="preflight", stage="preflight"), diagnostics.step("prepare"):
                prepare()
            current = _read_state(self.state_dir, sample)
            begin_installation_attempt(self.state_dir, current, previous)
            accepted = installation_view(current, "admin")

            def work():
                with diagnostics.context(_read_state(self.state_dir, sample)):
                    if previous and previous.get("status") in {"failed", "uninstall_failed"}:
                        diagnostics.emit("retry.started", previous_attempt_id=previous.get("attemptId"),
                                         completed_stages=[name for name, status in previous.get("stages", {}).items()
                                                           if status == "succeeded"])
                    try:
                        with diagnostics.step("operation") as outcome:
                            execute()
                            current = _read_state(self.state_dir, sample)
                            if current and current.get("status") in {"installing", "uninstalling"}:
                                self._fail(sample, "install_failed", "Installation execution returned without a terminal status; an administrator can retry.")
                                current = _read_state(self.state_dir, sample)
                            diagnostics.emit("operation.result", status=(current or {}).get("status"))
                            outcome["ok"] = (current or {}).get("status") in {"installed", "uninstalled"}
                    except Exception:
                        self._fail(sample, "install_failed", "Installation did not complete; an administrator can retry.")
                    finally:
                        lock.release()

            Thread(target=work, name=f"sample-{sample}", daemon=True).start()
            return accepted
        except Exception:
            self._fail(sample, "install_failed", "Installation could not start; an administrator can retry.")
            lock.release()
            raise
