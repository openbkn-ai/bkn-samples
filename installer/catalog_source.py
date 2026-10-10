"""Discover release metadata from the official repository; never execute sample code."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from jsonschema import Draft202012Validator, FormatChecker

from installer.studio_api import ApiError
from installer.state_store import write_json

REF_URL = "https://api.github.com/repos/openbkn-ai/bkn-samples/git/ref/heads/main"
RAW_PREFIX = "https://raw.githubusercontent.com/openbkn-ai/bkn-samples/"
SHA = re.compile(r"[0-9a-f]{40}")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("official metadata redirects are not permitted")


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_url(url: str, limit: int) -> bytes:
    request = Request(url, headers={"User-Agent": "OpenBKN-SampleCatalog", "Accept": "application/json"})
    with build_opener(NoRedirect()).open(request, timeout=10) as response:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("official metadata exceeds size limit")
        return data


def pinned_url(url: str) -> None:
    parsed = urlsplit(url)
    if (not url.startswith(RAW_PREFIX) or parsed.query or parsed.fragment or parsed.username
            or parsed.port or "%" in url or "\\" in url):
        raise ValueError("metadata must use the official raw repository at a commit SHA")
    parts = url[len(RAW_PREFIX):].split("/")
    if not SHA.fullmatch(parts[0]) or len(parts) < 2 or any(p in {"", ".", ".."} for p in parts[1:]):
        raise ValueError("metadata URL is not pinned to a commit")


class OfficialCatalog:
    def __init__(self, state_dir: Path, schema_path: Path, catalog_url: str | None = None):
        self.path = state_dir / "catalogs" / "official.json"
        self.lock = threading.Lock()
        self.refresh_lock = threading.Lock()
        self.last_attempt = -60.0
        self.catalog_url = catalog_url or ""
        if self.catalog_url:
            pinned_url(self.catalog_url)
            parts = self.catalog_url[len(RAW_PREFIX):].split("/")
            if len(parts) != 2 or parts[1] != "catalog.json" or not SHA.fullmatch(parts[0]):
                raise ValueError("pinned catalog URL must identify an official commit")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())
        self.cache = None
        self.result = {"status": "not_refreshed", "code": "", "checkedAt": None}
        if self.path.is_file():
            try:
                cached = json.loads(self.path.read_text(encoding="utf-8"), object_pairs_hook=object_pairs)
                self.validate(cached["catalog"], freshness=False)
                self.cache = cached
            except Exception:
                self.result = {"status": "failed", "code": "invalid_cache", "checkedAt": None}

    def validate(self, catalog: dict, freshness: bool = True) -> None:
        self.validator.validate(catalog)
        metadata = catalog["metadata"]
        expires_at = metadata.get("expiresAt")
        if freshness and expires_at and datetime.fromisoformat(expires_at.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            raise ValueError("catalog has expired")
        if metadata["sourceId"] != "openbkn-official" or metadata["channel"] != "stable":
            raise ValueError("expected official stable catalog")
        entries = catalog["spec"]["entries"]
        if len(entries) > 500:
            raise ValueError("catalog contains too many releases")
        identities = set()
        for entry in entries:
            identity = entry["sampleId"], entry["version"]
            if identity in identities:
                raise ValueError("duplicate release identity")
            identities.add(identity)
            for reference in [entry["manifest"], entry["verification"], *entry["releaseNotes"]["documents"]]:
                pinned_url(reference["url"])
            locales = [d["locale"] for d in entry["releaseNotes"]["documents"]]
            if len(locales) != len(set(locales)) or entry["releaseNotes"]["defaultLocale"] not in locales:
                raise ValueError("invalid notes locales")

    def metadata(self) -> dict:
        with self.lock:
            return {"supported": True, "lastSuccessfulRefreshAt": (self.cache or {}).get("fetchedAt"),
                    "revision": (self.cache or {}).get("commit"), **self.result}

    def entries(self) -> list[dict]:
        with self.lock:
            return list((self.cache or {}).get("catalog", {}).get("spec", {}).get("entries", []))

    def refresh(self) -> dict:
        with self.refresh_lock:
            if time.monotonic() - self.last_attempt < 60:
                return {**self.result, "throttled": True}
            self.last_attempt = time.monotonic()
            checked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            try:
                if self.catalog_url:
                    commit = self.catalog_url[len(RAW_PREFIX):].split("/", 1)[0]
                    catalog_url = self.catalog_url
                else:
                    ref = json.loads(read_url(REF_URL, 16 * 1024), object_pairs_hook=object_pairs)
                    commit = ref["object"]["sha"]
                    if not isinstance(commit, str) or not SHA.fullmatch(commit):
                        raise ValueError("invalid repository commit")
                    catalog_url = RAW_PREFIX + commit + "/catalog.json"
                catalog = json.loads(read_url(catalog_url, 2 * 1024 * 1024), object_pairs_hook=object_pairs)
                self.validate(catalog)
                previous = (self.cache or {}).get("catalog")
                if previous and catalog != previous:
                    if catalog["metadata"]["sequence"] <= previous["metadata"]["sequence"]:
                        raise ValueError("catalog sequence did not advance")
                    old_entries = {(e["sampleId"], e["version"]): e for e in previous["spec"]["entries"]}
                    new_entries = {(e["sampleId"], e["version"]): e for e in catalog["spec"]["entries"]}
                    for identity, old in old_entries.items():
                        if identity not in new_entries:
                            raise ValueError("historical release removed")
                        for field in ("manifest", "releaseNotes", "requires", "publishedAt", "verification"):
                            if old[field] != new_entries[identity][field]:
                                raise ValueError("published release rewritten")
                status = "unchanged" if previous == catalog else "updated"
                cached = {"commit": commit, "fetchedAt": checked_at, "catalog": catalog}
                write_json(self.path, cached)
                with self.lock:
                    self.cache = cached
                    self.result = {"status": status, "code": "", "checkedAt": checked_at}
            except HTTPError as error:
                with self.lock:
                    self.result = {"status": "failed", "code": "catalog_not_published" if error.code == 404 else "source_unavailable", "checkedAt": checked_at}
            except Exception:
                with self.lock:
                    self.result = {"status": "failed", "code": "source_unavailable", "checkedAt": checked_at}
            return dict(self.result)

    def notes(self, sample: str, version: str, locale: str) -> dict:
        entry = next((e for e in self.entries() if e["sampleId"] == sample and e["version"] == version), None)
        if entry is None:
            raise ApiError(404, "release_notes_unavailable", "version notes are unavailable")
        notes = entry["releaseNotes"]
        document = next((d for d in notes["documents"] if d["locale"] == locale), None)
        if document is None:
            document = next(d for d in notes["documents"] if d["locale"] == notes["defaultLocale"])
        try:
            data = read_url(document["url"], 256 * 1024)
            if "sha256:" + hashlib.sha256(data).hexdigest() != document["digest"]:
                raise ValueError("notes digest mismatch")
            content = data.decode("utf-8")
            if not content.strip():
                raise ValueError("empty notes")
            return {"sample": sample, "version": version, "resolvedLocale": document["locale"],
                    "content": content, "digest": document["digest"]}
        except Exception as error:
            raise ApiError(502, "release_notes_unavailable", "version notes could not be retrieved") from error
