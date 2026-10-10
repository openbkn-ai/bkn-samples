"""Package a local sample for review, without executing it or publishing a release."""

import argparse
import gzip
import hashlib
import io
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
NOTE = re.compile(r"release-notes\.([a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*)\.md")
DIRECTORIES = {"data", "db", "kn", "platform", "skills", "tools", "docs", "scripts"}
FILES = {"sample.yaml", "README.md", "LICENSE", "LICENSE.md", "run.sh", "dataset.lock",
         "vega_sql_execute.openapi.json"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def safe_path(path):
    # Check before resolving, so links cannot hide behind a contained target.
    for component in (path, *path.parents):
        require(not component.is_symlink(), f"symlink is not permitted: {component}")
    return path.resolve()


def included(relative):
    parts = relative.parts
    if any(p in {"tests", "__pycache__", ".venv", ".deployment", "node_modules"}
           or p.startswith(".") for p in parts):
        return False
    if relative.name in {"config.yaml", "config.poc.yaml", "smoke_report.json"}:
        return False
    if relative.suffix.lower() in {".pyc", ".pem", ".key", ".p12", ".pfx"}:
        return False
    return (len(parts) == 1 and relative.name in FILES) or parts[0] in DIRECTORIES


def build(sample_dir, version, output, data_image_ref=None):
    require(VERSION.fullmatch(version), "version must be MAJOR.MINOR.PATCH")
    sample_dir = safe_path(sample_dir.absolute())
    require(sample_dir.parent == ROOT / "samples", "sample must be a direct child of samples/")
    require(sample_dir.is_dir(), "sample directory is missing")
    prefix = sample_dir.relative_to(ROOT).as_posix() + "/"
    files = {}
    # Git's index is the explicit source allowlist. Untracked code/config is never bundled.
    for record in git("ls-files", "--stage", "-z", "--", prefix).split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, _, stage = metadata.decode("ascii").split()
        relative = Path(raw_path.decode("utf-8")[len(prefix):])
        if not included(relative):
            continue
        require(stage == "0" and mode in {"100644", "100755"},
                f"unmerged or non-regular tracked file: {relative}")
        files[relative] = 0o755 if mode == "100755" else 0o644
    notes_dir = sample_dir / "releases" / version
    safe_path(notes_dir)
    notes = []
    for path in sorted(notes_dir.glob("release-notes.*.md")):
        match = NOTE.fullmatch(path.name)
        require(match, f"invalid notes filename: {path.name}")
        files[path.relative_to(sample_dir)] = 0o644
        notes.append((path.relative_to(sample_dir), match[1]))
    require(notes, "version needs at least one release note document")
    require(Path("sample.yaml") in files, "sample.yaml must be tracked")

    snapshots = []
    total = 0
    for relative, mode in sorted(files.items()):
        path = sample_dir / relative
        safe_path(path)
        require(path.is_file(), f"missing regular file: {relative}")
        require(path.stat().st_size <= 128 * 1024 * 1024, f"file exceeds 128 MiB: {relative}")
        data = path.read_bytes()
        total += len(data)
        require(total <= 512 * 1024 * 1024, "candidate exceeds 512 MiB")
        snapshots.append((relative.as_posix(), mode, data))
    by_path = {p: data for p, _, data in snapshots}
    documents = []
    for relative, locale in notes:
        data = by_path[relative.as_posix()]
        require(len(data) <= 256 * 1024 and data.decode("utf-8").strip(),
                f"release notes must be nonempty UTF-8 and at most 256 KiB: {relative}")
        documents.append({"locale": locale, "path": relative.as_posix(), "digest": sha(data)})

    if data_image_ref is not None:
        require(re.fullmatch(r"[a-z0-9][a-z0-9./:_-]*@sha256:[a-f0-9]{64}", data_image_ref),
                "offline package needs a fixed data image digest")
        contract = yaml.safe_load(by_path["sample.yaml"].decode("utf-8"))
        components = contract["spec"]["components"]
        native_format = "bkn-directory" if "kn/network.bkn" in by_path else "kn-json"
        capabilities = ["vega.catalog", "knowledge-network.import." + native_format]
        capabilities.extend("execution." + component for component, key in
                            (("function", "functions"), ("skill", "skills")) if components[key])
        descriptor = {
            "apiVersion": "samples.openbkn.ai/offline.v1", "version": version,
            "dataImageRef": data_image_ref,
            "requires": {"installationProfiles": ["openbkn.ai/sample-install.v1"],
                         "requiredExtensions": [], "platformVersion": ">=0.2.0 <0.3.0",
                         "architectures": ["arm64", "amd64"],
                         "capabilities": capabilities},
            "releaseNotes": documents,
            "files": [{"path": p, "digest": sha(data)} for p, _, data in snapshots],
        }
        snapshots.append(("offline-release.json", 0o644,
                          json.dumps(descriptor, ensure_ascii=False, sort_keys=True).encode("utf-8")))

    output = safe_path(output.absolute())
    require(not output.is_relative_to(ROOT), "candidate output must be outside the source repository")
    output.mkdir(parents=True, exist_ok=True)
    target = output / sample_dir.name / version
    target.parent.mkdir(parents=True, exist_ok=True)
    safe_path(target)
    require(not target.exists(), "candidate already exists; use a fresh output directory")
    temporary = Path(tempfile.mkdtemp(prefix=".candidate-", dir=target.parent))
    try:
        archive = temporary / "package.tar.gz"
        with archive.open("wb") as stream:
            with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as tar:
                    for path, mode, data in snapshots:
                        info = tarfile.TarInfo(path)
                        info.size, info.mode, info.mtime = len(data), mode, 0
                        info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        tar.addfile(info, io.BytesIO(data))
        report = {
            "status": "candidate-not-verified",
            "sampleDirectory": sample_dir.name,
            "version": version,
            "source": {
                "repository": "https://github.com/openbkn-ai/bkn-samples",
                "commit": git("rev-parse", "HEAD").decode().strip(),
                "workingTreeChanges": bool(git("status", "--porcelain", "--", prefix)),
            },
            "package": {"path": archive.name, "digest": sha(archive.read_bytes()),
                        "size": archive.stat().st_size},
            "releaseNotes": documents,
            "files": [{"path": path, "mode": oct(mode), "size": len(data), "digest": sha(data)}
                      for path, mode, data in snapshots],
            "pending": ["native-model-validation", "platform-compatibility",
                        "fixed-artifact-installation", "scenario-acceptance",
                        "publication-manifest-and-verification"],
        }
        (temporary / "build.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.rename(target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample_dir", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--data-image-ref", help="Include offline metadata bound to this fixed image digest")
    args = parser.parse_args()
    try:
        target = build(args.sample_dir, args.version, args.output, args.data_image_ref)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Candidate build failed: {error}\n")
    print(f"Candidate created: {target}")
    print("Not platform verified; not published or installable through the official catalog.")


if __name__ == "__main__":
    main()
