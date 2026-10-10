"""Load one official fixed release into a private temporary install root.

This module never runs hooks or creates platform resources. The caller keeps the
catalog entry as the retry identity and owns the temporary directory lifetime.
"""

import hashlib
import json
import os
import re
import tarfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from jsonschema import Draft202012Validator, FormatChecker
import yaml

from installer.catalog_source import object_pairs, pinned_url, read_url
from installer.contract import load_sample, validate_document

MAX_ARCHIVE = 128 * 1024 * 1024
MAX_CONTENT = 512 * 1024 * 1024
MAX_FILE = 128 * 1024 * 1024
MAX_MEMBERS = 10000
PROFILE = "openbkn.ai/sample-install.v1"
CAPABILITIES = {"vega.catalog", "knowledge-network.import.kn-json",
                "knowledge-network.import.bkn-directory",
                "execution.function", "execution.skill"}


class UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        require(key not in result, "duplicate BKN frontmatter key")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def safe_path(value):
    require(isinstance(value, str) and value and "\\" not in value and "\x00" not in value,
            "invalid package path")
    parts = value.split("/")
    require(all(p not in {"", ".", ".."} for p in parts) and ":" not in parts[0],
            "package path escapes its root")
    return Path(*parts)


def compatibility(requires, platform_version, architecture, capabilities):
    """The first profile supports bounded, stable three-component version ranges."""
    require(requires["installationProfiles"] == [PROFILE] and not requires["requiredExtensions"],
            "unsupported install profile or required extension")
    require(architecture in requires["architectures"], "unsupported architecture")
    version = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", platform_version)
    require(version, "platform version has not been configured")
    current = tuple(map(int, version.groups()))
    terms = requires["platformVersion"].split()
    require(terms, "missing platform version range")
    for term in terms:
        match = re.fullmatch(r"(>=|<=|>|<|=)(\d+)\.(\d+)\.(\d+)", term)
        require(match, "unsupported platform version range")
        operator, *numbers = match.groups()
        target = tuple(map(int, numbers))
        require({">=": current >= target, "<=": current <= target, ">": current > target,
                 "<": current < target, "=": current == target}[operator], "incompatible platform version")
    required = set(requires["capabilities"])
    require(required <= CAPABILITIES and required <= set(capabilities), "required capability is unavailable")


def checked_json(reference, reader=read_url):
    pinned_url(reference["url"])
    data = reader(reference["url"], 2 * 1024 * 1024)
    require(sha(data) == reference["digest"], "release metadata digest mismatch")
    document = json.loads(data.decode("utf-8"), object_pairs_hook=object_pairs)
    require(isinstance(document, dict), "release metadata must be a JSON object")
    return document


def load_release(entry, schema_path, platform_version, architecture, capabilities, reader=read_url):
    require(entry["releaseStatus"] == "published", "release has been withdrawn")
    require(re.fullmatch(r"[a-z][a-z0-9-]{0,31}", entry["sampleId"]), "unsupported runtime sample identity")
    require(re.fullmatch(r"\d+\.\d+\.\d+", entry["version"]), "unsupported release version")
    compatibility(entry["requires"], platform_version, architecture, capabilities)
    sample = checked_json(entry["manifest"], reader)
    validator = Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")),
                                     format_checker=FormatChecker())
    validator.validate(sample)
    metadata, spec = sample["metadata"], sample["spec"]
    for key in ("sampleId", "version", "displayName", "summary"):
        require(metadata[key] == entry[key], "catalog and manifest identity differ")
    require(spec["requires"] == entry["requires"], "catalog requirements differ")
    require(spec["release"]["publishedAt"] == entry["publishedAt"], "catalog release date differs")
    require(spec["delivery"]["profile"] == PROFILE, "unsupported delivery profile")
    artifacts = spec["artifacts"]
    require(len(artifacts) == 2 and {a["type"] for a in artifacts} == {"archive", "oci-image"},
            "this profile requires one package and one database image")
    require(len({a["id"] for a in artifacts}) == 2, "duplicate artifact identity")
    package = next(a for a in artifacts if a["type"] == "archive")
    image = next(a for a in artifacts if a["type"] == "oci-image")
    expected_url = ("https://github.com/openbkn-ai/bkn-samples/releases/download/"
                    f"sample-{entry['sampleId']}-v{entry['version']}/package.tar.gz")
    require(package["locations"] == [expected_url], "package must use the official sample release asset")
    require(image["locations"] == ["oci://ghcr.io/openbkn-ai/bkn-samples"],
            "database image must use the official image repository")
    image_ref = "ghcr.io/openbkn-ai/bkn-samples@" + image["digest"]
    dependencies = spec["delivery"]["dataDependencies"]
    require(len(dependencies) == 1 and dependencies[0]["artifactId"] == image["id"],
            "this profile requires one database dependency")
    networks = spec["contents"]["knowledgeNetworks"]
    require(len(networks) == 1 and networks[0]["format"] in {"kn-json", "bkn-directory"},
            "this runtime requires one native KN JSON or BKN directory")
    contents = [c for group in spec["contents"].values() for c in group]
    require(len({c["contentId"] for c in contents}) == len(contents), "duplicate content identity")
    for content in contents:
        require(content["artifactId"] == package["id"], "contents must belong to the fixed package")
        safe_path(content["directory"])
        if "entrypoint" in content:
            safe_path(content["entrypoint"])
    require(all(e["contentId"] == networks[0]["contentId"] for e in spec["experience"]),
            "experience refers to another network")
    proof = checked_json(entry["verification"], reader)
    # Digest checking binds the reviewed receipt; it does not independently prove
    # the receipt's claims. Publication reviewers must inspect the actual evidence.
    for key, expected in {"sampleId": entry["sampleId"], "version": entry["version"],
                          "packageDigest": package["digest"], "dataImageRef": image_ref}.items():
        require(proof.get(key) == expected, "verification receipt refers to other artifacts")
    require(proof.get("freshInstallation") is True, "fresh installation evidence is required")
    checks = proof.get("checks")
    require(isinstance(checks, list) and all(isinstance(c, dict) for c in checks), "invalid verification checks")
    require(len({c.get("name") for c in checks}) == len(checks), "duplicate verification check")
    required_checks = {"database", "knowledge", "capabilities", "scenario"}
    require(required_checks <= {c.get("name") for c in checks if c.get("passed") is True},
            "verification checks have not passed")
    notes = {}
    published_notes = spec["release"]["releaseNotes"]
    require(entry["releaseNotes"]["defaultLocale"] == spec["release"]["defaultLocale"], "notes default locale differs")
    require(len({n["locale"] for n in published_notes}) == len(published_notes), "duplicate notes locale")
    documents = entry["releaseNotes"]["documents"]
    require(len({n["locale"] for n in documents}) == len(documents), "duplicate catalog notes locale")
    require({n["locale"] for n in documents} == {n["locale"] for n in published_notes}, "notes locales differ")
    for note in documents:
        original = next(n for n in published_notes if n["locale"] == note["locale"])
        safe_path(original["path"])
        require(note["digest"] == original["digest"], "notes digest differs")
        pinned_url(note["url"])
        data = reader(note["url"], 256 * 1024)
        require(sha(data) == note["digest"] and data.decode("utf-8").strip(), "invalid release notes")
        notes[note["locale"]] = {"locale": note["locale"], "content": data.decode("utf-8"), "digest": note["digest"]}
    require(spec["release"]["defaultLocale"] in notes, "missing default release notes")
    return {"manifest": sample, "package": package, "dataImageRef": image_ref,
            "releaseNotes": {"version": entry["version"], "defaultLocale": spec["release"]["defaultLocale"],
                             "documents": list(notes.values())}}


def asset_url(url, initial=False):
    parsed = urlsplit(url)
    require(parsed.scheme == "https" and not parsed.username and not parsed.password and not parsed.port
            and not parsed.fragment, "invalid release asset URL")
    require(parsed.hostname in ({"github.com"} if initial else {"release-assets.githubusercontent.com"}),
            "release asset redirected outside GitHub asset storage")


class AssetRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        asset_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_package(package, destination):
    url = package["locations"][0]
    asset_url(url, initial=True)
    require(not destination.exists(), "package destination already exists")
    hasher, total = hashlib.sha256(), 0
    try:
        with build_opener(AssetRedirect()).open(Request(url), timeout=30) as response, destination.open("xb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                require(total <= MAX_ARCHIVE, "release archive exceeds size limit")
                hasher.update(chunk)
                output.write(chunk)
        require("sha256:" + hasher.hexdigest() == package["digest"], "release archive digest mismatch")
        if "sizeBytes" in package:
            require(total == package["sizeBytes"], "release archive size differs")
        destination.chmod(0o600)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def extract_package(archive, sample_dir, package):
    require(archive.stat().st_size <= MAX_ARCHIVE, "release archive exceeds size limit")
    with archive.open("rb") as source:
        hasher = hashlib.sha256()
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    require("sha256:" + hasher.hexdigest() == package["digest"], "cached release archive digest mismatch")
    require(not sample_dir.exists(), "extraction requires a fresh directory")
    sample_dir.mkdir(parents=True, mode=0o700)
    total, names = 0, set()
    with tarfile.open(archive, "r:gz") as bundle:
        for number, member in enumerate(bundle, 1):
            require(number <= MAX_MEMBERS, "too many archive members")
            path = safe_path(member.name)
            require(member.isfile() and not member.sparse, "archive may contain only regular files")
            require(path not in names, "duplicate archive member")
            names.add(path)
            require(0 <= member.size <= MAX_FILE, "archive member exceeds size limit")
            total += member.size
            require(total <= MAX_CONTENT, "expanded archive exceeds size limit")
            target = sample_dir / path
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with bundle.extractfile(member) as source, target.open("xb") as output:
                remaining = member.size
                while remaining:
                    chunk = source.read(min(remaining, 1024 * 1024))
                    require(chunk, "truncated archive member")
                    output.write(chunk)
                    remaining -= len(chunk)
            # Reproducible candidate archives use the Unix epoch for member
            # mtimes.  Some package builders (notably zipfile) reject dates
            # before 1980, so normalize the private worktree timestamp without
            # changing the archived bytes or their digest.
            os.utime(target, (315532800, 315532800))
            target.chmod(0o700 if member.mode & 0o111 else 0o600)


def validate_package(sample_dir, release):
    sample = release["manifest"]
    document = load_sample(sample_dir)
    require(not validate_document(sample_dir, document), "package installation contract is invalid")
    require(document["metadata"]["name"] == sample["metadata"]["sampleId"], "package sample identity differs")
    dependency = sample["spec"]["delivery"]["dataDependencies"][0]
    database = document["spec"]["database"]
    require(database["name"] == dependency["databaseName"] and database["expectedTables"] == dependency["expectedTables"],
            "package database differs from release manifest")
    for group in sample["spec"]["contents"].values():
        for content in group:
            directory = sample_dir / safe_path(content["directory"])
            require(directory.is_dir(), "package content directory is missing")
            if "entrypoint" in content:
                require((directory / safe_path(content["entrypoint"])).is_file(), "package entrypoint is missing")
    network = sample["spec"]["contents"]["knowledgeNetworks"][0]
    network_root = sample_dir / safe_path(network["directory"])
    path = network_root / safe_path(network["entrypoint"])
    if network["format"] == "kn-json":
        model = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=object_pairs)
        require(isinstance(model, dict) and model.get("id") == document["spec"]["knowledgeNetwork"]["id"],
                "native KN identity differs from installation contract")
        objects = model.get("object_types")
        require(isinstance(objects, list) and all(isinstance(o, dict) for o in objects),
                "invalid native KN object types")
        object_ids = {o.get("id") for o in objects}
    else:
        require(network["entrypoint"] == "network.bkn" and path.is_file(),
                "BKN directory must contain network.bkn")
        text = path.read_text(encoding="utf-8")
        require(text.startswith("---\n"), "BKN network.bkn is missing frontmatter")
        _, _, frontmatter = text.partition("---\n")
        raw, separator, _ = frontmatter.partition("\n---")
        require(separator, "BKN network.bkn has an invalid frontmatter block")
        metadata = yaml.load(raw, Loader=UniqueLoader)
        require(isinstance(metadata, dict) and metadata.get("type") == "knowledge_network"
                and metadata.get("id") == document["spec"]["knowledgeNetwork"]["id"],
                "BKN network identity differs from installation contract")
        object_dir = network_root / "object_types"
        object_files = sorted(object_dir.glob("*.bkn"))
        require(object_files, "BKN directory has no object types")
        object_ids = set()
        for object_file in object_files:
            object_text = object_file.read_text(encoding="utf-8")
            require(object_text.startswith("---\n"), "BKN object type is missing frontmatter")
            _, _, object_frontmatter = object_text.partition("---\n")
            object_raw, object_separator, _ = object_frontmatter.partition("\n---")
            require(object_separator, "BKN object type has an invalid frontmatter block")
            object_metadata = yaml.load(object_raw, Loader=UniqueLoader)
            require(isinstance(object_metadata, dict) and object_metadata.get("type") == "object_type"
                    and isinstance(object_metadata.get("id"), str),
                    "BKN object type identity is invalid")
            object_ids.add(object_metadata["id"])
    for binding in sample["spec"]["delivery"]["bindings"]:
        require(binding["contentId"] == network["contentId"]
                and binding["dataDependencyId"] == dependency["id"] and binding["objectTypeId"] in object_ids,
                "release binding refers to undeclared content")
    for note in sample["spec"]["release"]["releaseNotes"]:
        path = sample_dir / "releases" / sample["metadata"]["version"] / safe_path(note["path"])
        require(path.is_file() and sha(path.read_bytes()) == note["digest"], "package release notes differ")
    return document
