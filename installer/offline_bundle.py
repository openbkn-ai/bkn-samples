"""Admin-imported fixed packages. No catalog fetch or hook execution on upload."""

import json
import re
import shutil
import tempfile
from pathlib import Path
from threading import Lock

from installer.catalog_source import object_pairs
from installer.contract import load_sample, validate_document
from installer.remote_bundle import compatibility, extract_package, require, safe_path, sha
from installer.remote_installation import executor_digest
from installer.state_store import write_json
from installer.studio_api import ApiError, _card, _read_state, timestamp


class OfflinePackages:
    def __init__(self, root, state_dir, runtime):
        self.root, self.state_dir, self.runtime = root, state_dir, runtime
        self.directory = state_dir / "offline"
        self.lock = Lock()

    def inspect(self, directory, digest):
        descriptor = directory / "offline-release.json"
        require(descriptor.stat().st_size <= 2 * 1024 * 1024, "offline metadata exceeds size limit")
        release = json.loads(descriptor.read_text(), object_pairs_hook=object_pairs)
        require(release.get("apiVersion") == "samples.openbkn.ai/offline.v1", "unsupported offline format")
        require(isinstance(release.get("version"), str) and re.fullmatch(r"\d+\.\d+\.\d+", release["version"]),
                "invalid offline version")
        require(isinstance(release.get("dataImageRef"), str) and
                re.fullmatch(r"[a-z0-9][a-z0-9./:_-]*@sha256:[a-f0-9]{64}", release["dataImageRef"]),
                "offline data image must have a fixed digest")
        compatibility(release["requires"], self.runtime.platform_version,
                      self.runtime.architecture, self.runtime.capabilities)
        document = load_sample(directory)
        require(not validate_document(directory, document), "invalid sample contract")
        require(re.fullmatch(r"[a-z][a-z0-9-]{0,31}", document["metadata"]["name"]), "invalid sample identity")
        require(document["spec"]["data"]["mode"] == "embedded", "offline package requires embedded data")
        files = release["files"]
        require(isinstance(files, list) and files, "missing file digests")
        expected = {}
        for item in files:
            path = safe_path(item["path"]).as_posix()
            require(path not in expected and path != "offline-release.json", "duplicate or reserved file")
            expected[path] = item["digest"]
        actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*")
                  if p.is_file() and p != descriptor}
        require(actual == set(expected), "offline file inventory differs")
        for path, expected_digest in expected.items():
            require(sha((directory / path).read_bytes()) == expected_digest, "offline file digest differs")
        notes = []
        for note in release["releaseNotes"]:
            require(re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", note["locale"]), "invalid notes locale")
            path = safe_path(note["path"]).as_posix()
            require(expected.get(path) == note["digest"], "notes digest differs")
            require((directory / path).stat().st_size <= 256 * 1024, "notes exceed size limit")
            content = (directory / path).read_text(encoding="utf-8")
            require(content.strip(), "empty release notes")
            notes.append({"locale": note["locale"], "content": content, "digest": note["digest"]})
        require(notes and len({n["locale"] for n in notes}) == len(notes), "missing or duplicate notes")
        return {"sample": document["metadata"]["name"], "version": release["version"],
                "packageDigest": digest, "manifestSha256": sha((directory / "sample.yaml").read_bytes())[7:],
                "document": document, "dataImageRef": release["dataImageRef"],
                "releaseNotes": {"version": release["version"], "defaultLocale": notes[0]["locale"], "documents": notes}}

    def import_package(self, archive, role):
        if role != "admin":
            raise ApiError(403, "forbidden", "an administrator must import the sample")
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.lock, tempfile.TemporaryDirectory(dir=self.directory) as temporary:
            try:
                digest = sha(archive.read_bytes())
                extracted = Path(temporary) / "sample"
                extract_package(archive, extracted, {"digest": digest})
                release = self.inspect(extracted, digest)
                destination = self.directory / release["sample"]
                if destination.exists():
                    existing = json.loads((destination / "release.json").read_text())
                    require(existing["packageDigest"] == digest, "sample already imported with another package")
                    return {"sample": release["sample"], "version": release["version"], "packageDigest": digest}
                used = sum(p.stat().st_size for p in self.directory.glob("*/package.tar.gz"))
                require(used + archive.stat().st_size <= 1024 * 1024 * 1024, "offline cache exceeds 1 GiB")
                staged = Path(temporary) / "stored"
                staged.mkdir(mode=0o700)
                shutil.copyfile(archive, staged / "package.tar.gz")
                (staged / "package.tar.gz").chmod(0o600)
                write_json(staged / "release.json", release)
                staged.rename(destination)
                return {"sample": release["sample"], "version": release["version"], "packageDigest": digest}
            except (ValueError, KeyError, TypeError, OSError) as error:
                raise ApiError(400, "invalid_package", "offline package is invalid or conflicts with an imported package") from error

    def releases(self):
        return [json.loads(p.read_text()) for p in sorted(self.directory.glob("*/release.json"))]

    def find(self, sample):
        return next((r for r in self.releases() if r["sample"] == sample), None)

    def merge(self, result, role):
        result["canImport"] = role == "admin"
        for release in self.releases():
            document = release["document"]
            spec = document["spec"]
            item = {**document["metadata"], **spec["studio"], "manifestSha256": release["manifestSha256"],
                    "expectedTables": spec["database"]["expectedTables"], "components": spec["components"],
                    "knowledgeNetworkId": spec["knowledgeNetwork"]["id"],
                    "knowledgeNetworkDisplayName": spec["knowledgeNetwork"]["displayName"],
                    "releaseNotes": release["releaseNotes"]}
            old = next((c for c in result["samples"] if c["name"] == release["sample"]), None)
            card = _card(item, release["version"], _read_state(self.state_dir, release["sample"]), role, False)
            card["source"] = "offline"
            card["versions"][0]["manifestSha256"] = release["manifestSha256"]
            if old:
                result["samples"][result["samples"].index(old)] = card
            else:
                result["samples"].append(card)

    def prepare(self, release, retry=False):
        sample = release["sample"]
        current = _read_state(self.state_dir, sample)
        self.runtime.require_executor()
        if retry:
            require(current and current.get("status") == "failed", "only a failed installation can be retried")
            fixed = current.get("offlineRelease") or {}
            require(fixed.get("packageDigest") == release["packageDigest"] and
                    fixed.get("executorDigest") == executor_digest(self.root) and
                    fixed.get("executorImage") == self.runtime.executor_image, "retry requires original artifacts")
            current["status"] = "installing"
            current.pop("error", None)
        else:
            if current:
                code = {"installed": "already_installed", "failed": "use_retry", "installing": "already_installing"}.get(current.get("status"))
                if code:
                    raise ApiError(409, code, "an installation already exists")
            current = {"id": f"inst-{sample}", "sample": sample, "version": release["version"],
                       "status": "installing", "stages": {}, "startedAt": timestamp(),
                       "manifestSha256": release["manifestSha256"], "packageDigest": release["packageDigest"],
                       "dataImageRef": release["dataImageRef"], "releaseNotesSnapshot": release["releaseNotes"],
                       "offlineRelease": {"packageDigest": release["packageDigest"],
                                          "executorDigest": executor_digest(self.root),
                                          "executorImage": self.runtime.executor_image}}
        write_json(self.state_dir / f"{sample}.json", current)

    def execute(self, release, install, retry=False):
        with tempfile.TemporaryDirectory(dir=self.directory) as temporary:
            root = Path(temporary)
            sample_dir = root / "samples" / release["sample"]
            extract_package(self.directory / release["sample"] / "package.tar.gz", sample_dir,
                            {"digest": release["packageDigest"]})
            require(self.inspect(sample_dir, release["packageDigest"]) == release, "cached offline package changed")
            (root / "VERSION").write_text(release["version"])
            return install(root, release["version"], release["dataImageRef"], retry)
