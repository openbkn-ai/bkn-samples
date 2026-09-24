"""Pin a sample release to one version shared by the git tag, VERSION, and image tag."""

from __future__ import annotations

import argparse
import re
import sys

from installer.contract import OFFICIAL_SOURCE_REPO, ContractError, read_version
from installer.deploy_database import GHCR_IMAGE, SWR_IMAGE

VERSION_RE = re.compile(r"\d+\.\d+\.\d+")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ReleaseError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def assert_release_tag(tag: str, version: str) -> str:
    """Return the image tag. It is the VERSION value, never latest."""
    normalized = tag[1:] if tag.startswith("v") and VERSION_RE.fullmatch(tag[1:]) else tag
    if normalized == "latest" or not VERSION_RE.fullmatch(normalized):
        raise ReleaseError(f"release tag {tag!r} is not a pinned MAJOR.MINOR.PATCH version")
    if normalized != version:
        raise ReleaseError(f"release tag {tag!r} does not match VERSION {version}")
    return version


def image_refs(version: str) -> tuple[str, str]:
    pinned = assert_release_tag(version, version)
    return f"{SWR_IMAGE}:{pinned}", f"{GHCR_IMAGE}:{pinned}"


def assert_same_digest(left: str, right: str) -> str:
    swr = left.strip().strip('"')
    ghcr = right.strip().strip('"')
    if not DIGEST_RE.fullmatch(swr) or not DIGEST_RE.fullmatch(ghcr):
        raise ReleaseError("registry digests must be sha256 values")
    if swr != ghcr:
        raise ReleaseError("SWR and GHCR manifest digests differ")
    return swr


def merge_catalog(pinned_version: str, image_index: dict, repo_index: dict) -> dict:
    """Mark the catalog unusable when the pinned version, image, or repo disagree."""
    image_ok = _source_ok(image_index, pinned_version)
    repo_ok = _source_ok(repo_index, pinned_version)
    if not image_ok or not repo_ok:
        samples = _unavailable(_samples(image_index) or _samples(repo_index), "source_rejected")
        return {"sourceRejected": True, "samples": samples}
    merged = []
    repo_by_name = {item["name"]: item for item in _samples(repo_index)}
    for image_sample in _samples(image_index):
        repo_sample = repo_by_name.get(image_sample.get("name"))
        if repo_sample is None or image_sample.get("manifestSha256") != repo_sample.get("manifestSha256"):
            merged.append({**image_sample, "status": "unavailable", "installable": False, "code": "source_rejected"})
            continue
        merged.append({**repo_sample, "status": "not_installed", "installable": True, "code": ""})
    return {"sourceRejected": False, "samples": merged}


def _source_ok(index: dict, pinned_version: str) -> bool:
    return (
        isinstance(index, dict)
        and index.get("sourceRepo") == OFFICIAL_SOURCE_REPO
        and index.get("version") == pinned_version
    )


def _samples(index: dict) -> list[dict]:
    samples = index.get("samples") if isinstance(index, dict) else None
    return list(samples) if isinstance(samples, list) else []


def _unavailable(samples: list[dict], code: str) -> list[dict]:
    return [{**item, "status": "unavailable", "installable": False, "code": code} for item in samples]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a pinned bkn-samples release.")
    sub = parser.add_subparsers(dest="command", required=True)
    tag = sub.add_parser("check-tag")
    tag.add_argument("--tag", required=True)
    tag.add_argument("--root", default=".")
    digests = sub.add_parser("check-digests")
    digests.add_argument("--left", required=True)
    digests.add_argument("--right", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "check-tag":
            version = read_version(__import__("pathlib").Path(args.root))
            print(assert_release_tag(args.tag, version))
        else:
            print(assert_same_digest(args.left, args.right))
    except (ReleaseError, ContractError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
