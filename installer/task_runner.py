"""One worker per bundled sample, with state persisted before HTTP acceptance."""

from pathlib import Path
import re
from threading import Lock, Thread

from installer.state_store import write_json
from installer.studio_api import ApiError, _read_state, installation_view, timestamp


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
        if not current or current.get("status") != "installing":
            return
        current["status"] = "failed"
        current["error"] = {"code": code, "message": message}
        current["finishedAt"] = timestamp()
        stages = current.setdefault("stages", {})
        for stage, status in list(stages.items()):
            if status == "running":
                stages[stage] = "failed"
        if not stages:
            stages["database"] = "failed"
        write_json(self.state_dir / f"{sample}.json", current)

    def submit(self, sample, prepare, execute):
        lock = self.locks.get(sample)
        if lock is None:
            raise ApiError(404, "install_failed", "unknown sample")
        if not lock.acquire(blocking=False):
            raise ApiError(409, "already_installing", "an installation is already running")
        try:
            prepare()
            accepted = installation_view(_read_state(self.state_dir, sample), "admin")

            def work():
                try:
                    execute()
                    self._fail(sample, "install_failed", "Installation did not complete; an administrator can retry.")
                except Exception:
                    # Expected failures already persist their details. Never expose an
                    # unexpected exception, which could contain credentials or commands.
                    self._fail(sample, "install_failed", "Installation did not complete; an administrator can retry.")
                finally:
                    lock.release()

            Thread(target=work, name=f"sample-{sample}", daemon=True).start()
            return accepted
        except Exception:
            self._fail(sample, "install_failed", "Installation could not start; an administrator can retry.")
            lock.release()
            raise
