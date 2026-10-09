"""Persist a release choice before acceptance and prepare its fixed files in a worker."""

import copy
import hashlib
import re
import tempfile
from pathlib import Path

from installer.remote_bundle import compatibility, download_package, extract_package, load_release, validate_package
from installer.state_store import write_json
from installer.studio_api import ApiError, _read_state, timestamp


def executor_digest(root):
    """Bind retries to the installed executor source, independent of the sample VERSION."""
    hasher = hashlib.sha256()
    for path in sorted((root / "installer").rglob("*")):
        if path.is_file() and "tests" not in path.relative_to(root / "installer").parts and path.suffix in {".py", ".sh", ".json"}:
            hasher.update(path.relative_to(root).as_posix().encode())
            hasher.update(b"\0")
            hasher.update(path.read_bytes())
    return "sha256:" + hasher.hexdigest()


class RemoteInstallation:
    def __init__(self, root, state_dir, platform_version, architecture, capabilities, executor_image=""):
        self.root, self.state_dir = root, state_dir
        self.platform_version, self.architecture = platform_version, architecture
        self.capabilities = capabilities
        self.executor_digest = executor_digest(root)
        self.executor_image = executor_image

    def require_executor(self):
        if not re.fullmatch(r"[a-z0-9][a-z0-9./:_-]*@sha256:[0-9a-f]{64}", self.executor_image):
            raise ValueError("remote installation requires a fixed executor image")

    def prepare(self, entry):
        sample = entry["sampleId"]
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", sample):
            raise ApiError(409, "runtime_upgrade_required", "unsupported runtime sample identity")
        if entry["releaseStatus"] != "published":
            raise ApiError(409, "release_withdrawn", "release has been withdrawn")
        try:
            self.require_executor()
            compatibility(entry["requires"], self.platform_version, self.architecture, self.capabilities)
        except ValueError as error:
            raise ApiError(409, "runtime_upgrade_required", "release requirements are not supported") from error
        current = _read_state(self.state_dir, sample)
        if current and current.get("status") in {"installed", "failed", "installing"}:
            code = {"installed": "already_installed", "failed": "use_retry", "installing": "already_installing"}[current["status"]]
            raise ApiError(409, code, "an installation already exists")
        current = {"id": f"inst-{sample}", "sample": sample, "version": entry["version"],
                   "status": "installing", "stages": {}, "startedAt": timestamp(),
                   "manifestSha256": entry["manifest"]["digest"].removeprefix("sha256:"),
                   "remoteRelease": {"entry": copy.deepcopy(entry), "executorDigest": self.executor_digest,
                                     "executorImage": self.executor_image}}
        write_json(self.state_dir / f"{sample}.json", current)

    def prepare_retry(self, sample, installation_id):
        current = _read_state(self.state_dir, sample)
        if not current or current.get("id") != installation_id:
            raise ApiError(404, "install_failed", "installation not found")
        if current.get("status") != "failed":
            raise ApiError(409, "already_installing", "only a failed installation can be retried")
        fixed = current.get("remoteRelease") or {}
        if fixed.get("executorDigest") != self.executor_digest or fixed.get("executorImage") != self.executor_image:
            raise ApiError(409, "version_changed", "retry requires the original executor source")
        entry = fixed.get("entry") or {}
        if entry.get("sampleId") != sample or entry.get("version") != current.get("version"):
            raise ApiError(409, "version_changed", "retry release identity differs")
        try:
            self.require_executor()
            compatibility(entry["requires"], self.platform_version, self.architecture, self.capabilities)
        except ValueError as error:
            raise ApiError(409, "runtime_upgrade_required", "release requirements are not supported") from error
        current["status"] = "installing"
        current.pop("error", None)
        current.pop("finishedAt", None)
        write_json(self.state_dir / f"{sample}.json", current)

    def execute(self, sample, install, *, retry=False, reader=None, downloader=download_package):
        """install receives (temporary root, release version, fixed data image, retry).

        Authorization belongs to the outer worker callback and is never written
        into the plan or archive cache. Exceptions are persisted by its runner.
        """
        current = _read_state(self.state_dir, sample)
        require_plan = current and current.get("status") == "installing" and current.get("remoteRelease")
        if (not require_plan or current["remoteRelease"]["executorDigest"] != self.executor_digest
                or current["remoteRelease"].get("executorImage") != self.executor_image):
            raise ValueError("fixed remote installation plan is unavailable")
        entry = current["remoteRelease"]["entry"]
        release = load_release(entry, self.root / "protocol/draft/schemas/sample.schema.json",
                               self.platform_version, self.architecture, self.capabilities,
                               **({"reader": reader} if reader else {}))
        work = self.state_dir / "work"
        work.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.TemporaryDirectory(prefix=f"{sample}-", dir=work) as temporary:
            directory = Path(temporary)
            archive = directory / "package.tar.gz"
            downloader(release["package"], archive)
            root = directory / "root"
            sample_dir = root / "samples" / sample
            extract_package(archive, sample_dir, release["package"])
            validate_package(sample_dir, release)
            (root / "VERSION").write_text(entry["version"], encoding="utf-8")
            current.update({"releaseNotesSnapshot": release["releaseNotes"],
                            "dataImageRef": release["dataImageRef"],
                            "packageDigest": release["package"]["digest"]})
            write_json(self.state_dir / f"{sample}.json", current)
            return install(root, entry["version"], release["dataImageRef"], retry)
