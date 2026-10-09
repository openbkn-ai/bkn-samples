"""Read version notes bundled with a sample; no network or executable content."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from installer.contract import ContractError

VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
LOCALE = re.compile(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")


def bundled_notes(sample_dir: Path, version: str) -> dict | None:
    if not VERSION.fullmatch(version):
        raise ContractError(["release notes version must be MAJOR.MINOR.PATCH"])
    folder = sample_dir / "releases" / version
    if not folder.exists():
        return None  # Old v1alpha1 samples may not yet have version notes.
    documents = []
    for path in sorted(folder.glob("release-notes.*.md")):
        locale = path.name[len("release-notes."):-len(".md")]
        if not LOCALE.fullmatch(locale):
            raise ContractError([f"invalid release notes locale: {path.name}"])
        if path.is_symlink() or not path.resolve().is_relative_to(sample_dir.resolve()):
            raise ContractError([f"release notes escapes sample: {path.name}"])
        if path.stat().st_size > 256 * 1024:
            raise ContractError([f"release notes must be nonempty and at most 256 KiB: {path.name}"])
        data = path.read_bytes()
        content = data.decode("utf-8")
        if not content.strip():
            raise ContractError([f"release notes must be nonempty: {path.name}"])
        documents.append({"locale": locale, "content": content,
                          "digest": "sha256:" + hashlib.sha256(data).hexdigest()})
    if not documents:
        raise ContractError([f"no release notes for {sample_dir.name}/{version}"])
    default_locale = "zh-CN" if any(d["locale"] == "zh-CN" for d in documents) else documents[0]["locale"]
    return {"version": version, "defaultLocale": default_locale, "documents": documents}
