"""Offline publication metadata validation; never executes or downloads samples."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

SCHEMAS = Path(__file__).resolve().parents[2] / "protocol/draft/schemas"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(values, label):
    values = list(values)
    require(len(values) == len(set(values)), f"duplicate {label}")


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=object_pairs)


def digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def relative_path(value):
    require(value and "\\" not in value and "\x00" not in value,
            f"invalid package path: {value!r}")
    parts = value.split("/")
    require(all(part and part not in {".", ".."} for part in parts),
            f"unsafe package path: {value!r}")
    require(":" not in parts[0], f"absolute package path: {value!r}")
    return Path(*parts)


def local_file(root, value):
    relative = relative_path(value)
    current = root
    for part in relative.parts:
        current = current / part
        require(not current.is_symlink(), f"symlink is not permitted: {current}")
    require(current.resolve().is_relative_to(root.resolve()), f"path escapes root: {current}")
    require(current.is_file(), f"missing file: {current}")
    return current


def location(value, schemes):
    parsed = urlsplit(value)
    require(parsed.scheme in schemes and parsed.hostname and not parsed.username
            and not parsed.password and not parsed.fragment,
            f"invalid artifact/document location: {value!r}")


def official_file(root, reference):
    prefix = "https://raw.githubusercontent.com/openbkn-ai/bkn-samples/"
    url = reference["url"]
    parsed = urlsplit(url)
    require(url.startswith(prefix) and not parsed.query and not parsed.fragment
            and not parsed.username and not parsed.port and "%" not in url and "\\" not in url,
            "official metadata must use a pinned raw repository URL")
    commit, separator, path = url[len(prefix):].partition("/")
    require(separator and re.fullmatch(r"[0-9a-f]{40}", commit), "metadata commit is not fixed")
    file = local_file(root, path)
    require(digest(file) == reference["digest"], f"metadata digest mismatch: {path}")
    committed = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=root,
                               capture_output=True, check=False)
    require(committed.returncode == 0 and committed.stdout == file.read_bytes(),
            f"metadata is not present at the advertised commit: {path}")
    return file


def validate_catalog(root, official=False):
    validators = {}
    for name in ("sample", "catalog"):
        schema = load(SCHEMAS / f"{name}.schema.json")
        Draft202012Validator.check_schema(schema)
        validators[name] = Draft202012Validator(schema, format_checker=FormatChecker())
    catalog = load(local_file(root, "catalog.json"))
    validators["catalog"].validate(catalog)
    entries = catalog["spec"]["entries"]
    if official:
        require(catalog["metadata"]["sourceId"] == "openbkn-official"
                and catalog["metadata"]["channel"] == "stable", "expected official stable catalog")
        require(len(entries) <= 500, "too many catalog releases")
    unique(((e["sampleId"], e["version"]) for e in entries), "catalog release")
    releases = {}
    for entry in entries:
        identity = (entry["sampleId"], entry["version"])
        folder = f"{identity[0]}/releases/{identity[1]}"
        manifest = (official_file(root, entry["manifest"]) if official
                    else local_file(root, f"{folder}/sample.json"))
        if official:
            folder = manifest.parent.relative_to(root).as_posix()
            require(folder.startswith("samples/") and folder.endswith(f"/releases/{identity[1]}"),
                    "official manifest must be in its sample release directory")
            proof = official_file(root, entry["verification"])
            require(proof.parent == manifest.parent, "verification must accompany the release")
            require(isinstance(load(proof), dict), "verification must be a JSON object")
        sample = load(manifest)
        validators["sample"].validate(sample)
        require((sample["metadata"]["sampleId"], sample["metadata"]["version"]) == identity,
                f"release identity mismatch: {folder}")
        require(digest(manifest) == entry["manifest"]["digest"], f"manifest digest mismatch: {folder}")
        location(entry["manifest"]["url"], {"https"})
        location(entry["verification"]["url"], {"https"})
        spec = sample["spec"]
        for key in ("requires",):
            require(entry[key] == spec[key], f"catalog {key} mismatch: {folder}")
        for key in ("displayName", "summary"):
            require(entry[key] == sample["metadata"][key], f"catalog {key} mismatch: {folder}")
        release = spec["release"]
        require(entry["publishedAt"] == release["publishedAt"], f"release date mismatch: {folder}")
        notes = release["releaseNotes"]
        unique((n["locale"] for n in notes), "notes locale")
        unique((n["path"] for n in notes), "notes path")
        notes_by_locale = {n["locale"]: n for n in notes}
        require(release["defaultLocale"] in notes_by_locale, f"missing default notes: {folder}")
        for note in notes:
            path = local_file(root, f"{folder}/{note['path']}")
            require(path.read_text(encoding="utf-8").strip(), f"empty release notes: {path}")
            require(digest(path) == note["digest"], f"release notes digest mismatch: {path}")
        catalog_notes = entry["releaseNotes"]
        require(catalog_notes["defaultLocale"] == release["defaultLocale"], "notes default locale mismatch")
        unique((n["locale"] for n in catalog_notes["documents"]), "catalog notes locale")
        require({n["locale"] for n in catalog_notes["documents"]} == set(notes_by_locale),
                "catalog notes locale set mismatch")
        for note in catalog_notes["documents"]:
            location(note["url"], {"https"})
            require(note["digest"] == notes_by_locale[note["locale"]]["digest"], "catalog notes digest mismatch")
            if official:
                path = official_file(root, note)
                expected = local_file(root, f"{folder}/{notes_by_locale[note['locale']]['path']}")
                require(path == expected, "catalog notes URL points to another file")
        artifacts = {a["id"]: a for a in spec["artifacts"]}
        unique((a["id"] for a in spec["artifacts"]), "artifact id")
        for artifact in artifacts.values():
            for url in artifact["locations"]:
                location(url, {"oci"} if artifact["type"] == "oci-image" else {"https"})
        contents = [c for group in spec["contents"].values() for c in group]
        unique((c["contentId"] for c in contents), "content id")
        unique(((c["artifactId"], c["directory"]) for c in contents), "content location")
        for content in contents:
            require(content["artifactId"] in artifacts, "unknown content artifact")
            require(artifacts[content["artifactId"]]["type"] == "archive", "content requires archive")
            relative_path(content["directory"])
            if "entrypoint" in content:
                relative_path(content["entrypoint"])
        networks = {c["contentId"] for c in spec["contents"]["knowledgeNetworks"]}
        delivery = spec["delivery"]
        require(delivery["profile"] in spec["requires"]["installationProfiles"], "undeclared profile")
        dependencies = delivery["dataDependencies"]
        unique((d["id"] for d in dependencies), "data dependency id")
        dependency_ids = {d["id"] for d in dependencies}
        for dependency in dependencies:
            require(dependency["artifactId"] in artifacts, "unknown dependency artifact")
        unique(((b["contentId"], b["objectTypeId"]) for b in delivery["bindings"]), "object binding")
        for binding in delivery["bindings"]:
            require(binding["contentId"] in networks, "unknown binding network")
            require(binding["dataDependencyId"] in dependency_ids, "unknown binding dependency")
        for experience in spec["experience"]:
            require(experience["contentId"] in networks, "unknown experience network")
        for extension in spec["requires"]["requiredExtensions"]:
            require(extension in spec.get("extensions", {}), "missing required extension")
        releases[identity] = entry
    return catalog, releases


def compare_baseline(current, baseline):
    current_catalog, current_entries = current
    baseline_catalog, baseline_entries = baseline
    require(current_catalog["metadata"]["sourceId"] == baseline_catalog["metadata"]["sourceId"],
            "baseline source mismatch")
    require(current_catalog["metadata"]["channel"] == baseline_catalog["metadata"]["channel"],
            "baseline channel mismatch")
    if current_catalog != baseline_catalog:
        require(current_catalog["metadata"]["sequence"] > baseline_catalog["metadata"]["sequence"],
                "catalog sequence must advance when contents change")
    # Tombstones keep historical releases discoverable; withdrawal does not rewrite content.
    for identity, previous in baseline_entries.items():
        require(identity in current_entries, f"release removed; retain withdrawn entry: {identity}")
        entry = current_entries[identity]
        for key in ("manifest", "releaseNotes", "requires", "publishedAt", "verification"):
            require(entry[key] == previous[key], f"immutable release changed: {identity} / {key}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="local catalog root (catalog.json and release files)")
    parser.add_argument("--baseline", type=Path, help="trusted prior catalog root; enforces release immutability")
    parser.add_argument("--official", action="store_true", help="verify official metadata against pinned Git objects")
    parser.add_argument("--baseline-catalog", type=Path, help="catalog JSON extracted from the trusted base commit")
    args = parser.parse_args()
    try:
        current = validate_catalog(args.root, official=args.official)
        if args.baseline:
            compare_baseline(current, validate_catalog(args.baseline, official=args.official))
        if args.baseline_catalog:
            baseline = load(args.baseline_catalog)
            compare_baseline(current, (baseline, {(e["sampleId"], e["version"]): e
                                                  for e in baseline["spec"]["entries"]}))
    except (ValueError, OSError, SchemaError, ValidationError) as error:
        parser.exit(1, f"Publication validation failed: {error}\n")
    print(f"Publication metadata valid: {len(current[1])} release(s).")
    print("Artifact bytes, native BKN/KN models and platform installation are not verified.")


if __name__ == "__main__":
    main()
