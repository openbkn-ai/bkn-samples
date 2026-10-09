"""Merge official releases with bundled cards without losing installation state."""

import re

from installer.remote_bundle import compatibility
from installer.studio_api import _card, _read_state


def merge_remote(result, entries, state_dir, role, runtime):
    by_name = {item["name"]: item for item in result["samples"]}
    fixed_entries = {(e["sampleId"], e["version"]): e for e in entries}
    for path in state_dir.glob("*.json"):
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", path.stem):
            continue
        state = _read_state(state_dir, path.stem) or {}
        entry = (state.get("remoteRelease") or {}).get("entry")
        if entry and entry.get("sampleId") == path.stem and entry.get("version") == state.get("version"):
            fixed_entries.setdefault((entry["sampleId"], entry["version"]), entry)
    groups = {}
    for entry in fixed_entries.values():
        groups.setdefault(entry["sampleId"], []).append(entry)
    for name, releases in groups.items():
        releases.sort(key=lambda e: tuple(map(int, e["version"].split("."))), reverse=True)
        versions = []
        for entry in releases:
            reason = "release_withdrawn" if entry["releaseStatus"] != "published" else ""
            if not reason:
                try:
                    runtime.require_executor()
                    compatibility(entry["requires"], runtime.platform_version, runtime.architecture, runtime.capabilities)
                    if len(name) > 32 or not name[0].isalpha():
                        raise ValueError("unsupported sample identity")
                except ValueError:
                    reason = "runtime_upgrade_required"
            versions.append({"version": entry["version"], "hasReleaseNotes": True,
                             "manifestSha256": entry["manifest"]["digest"].removeprefix("sha256:"),
                             "installable": not reason and role == "admin", "reason": reason,
                             "releaseStatus": entry["releaseStatus"], "publishedAt": entry["publishedAt"]})
        published = [e for e in releases if e["releaseStatus"] == "published"]
        selected = next((e for e, v in zip(releases, versions) if not v["reason"]), (published or releases)[0])
        state = _read_state(state_dir, name)
        old = by_name.get(name)
        if old and state and not state.get("remoteRelease"):
            card = old
        elif old and not any(not v["reason"] for v in versions) and not (state or {}).get("remoteRelease"):
            card = old
        else:
            selected_view = next(v for v in versions if v["version"] == selected["version"])
            item = {"name": name, "displayName": selected["displayName"], "summary": selected["summary"],
                    "manifestSha256": selected_view["manifestSha256"],
                    "status": "not_installed" if not selected_view["reason"] else "unavailable",
                    "code": selected_view["reason"]}
            if state and state.get("remoteRelease"):
                # A release becoming unavailable does not erase what was installed.
                item["status"] = "not_installed"
                item["knowledgeNetworkId"] = (state.get("resources") or {}).get("knowledgeNetworkId", "")
                item["releaseNotes"] = state.get("releaseNotesSnapshot")
            card = _card(item, selected["version"], state, role, False)
            card["installable"] = card["installable"] and not selected_view["reason"]
            if old:
                result["samples"][result["samples"].index(old)] = card
            else:
                result["samples"].append(card)
        card["latestPublishedVersion"] = published[0]["version"] if published else None
        existing = {v["version"] for v in card["versions"]}
        if card is old:
            card["versions"].extend(v for v in versions if v["version"] not in existing)
        else:
            card["versions"] = versions
    return result
