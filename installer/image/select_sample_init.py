"""Select an image's reviewed database hook by its sample manifest identity."""

import re
import sys
from pathlib import Path

import yaml


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError("duplicate manifest key")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def select(root, sample_id):
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", sample_id):
        raise ValueError("invalid BKN_SAMPLE_ID")
    matches = []
    for directory in sorted(root.iterdir()):
        manifest = directory / "sample.yaml"
        if directory.is_symlink() or not directory.is_dir() or not manifest.exists():
            continue
        if manifest.is_symlink() or manifest.stat().st_size > 256 * 1024:
            raise ValueError("unsafe image manifest")
        document = yaml.load(manifest.read_text(encoding="utf-8"), Loader=UniqueLoader)
        if not isinstance(document, dict):
            raise ValueError("invalid image manifest")
        metadata = document.get("metadata", {})
        if not isinstance(metadata, dict) or metadata.get("name") != sample_id:
            continue
        if document.get("apiVersion") != "samples.openbkn.ai/v1alpha1" or document.get("kind") != "Sample":
            raise ValueError("unsupported image manifest")
        hook = document["spec"]["hooks"]["dbInit"]
        if not isinstance(hook, str) or "\\" in hook or "\x00" in hook:
            raise ValueError("invalid database hook")
        parts = hook.split("/")
        if any(part in {"", ".", ".."} for part in parts) or ":" in parts[0]:
            raise ValueError("unsafe database hook")
        path = directory
        for part in parts:
            path = path / part
            if path.is_symlink():
                raise ValueError("symlink database hook")
        if not path.is_file():
            raise ValueError("missing database hook")
        matches.append(path)
    if len(matches) != 1:
        raise ValueError("BKN_SAMPLE_ID must identify exactly one sample shipped in this image")
    return matches[0]


if __name__ == "__main__":
    try:
        print(select(Path(sys.argv[1]), sys.argv[2]))
    except (ValueError, OSError, KeyError, TypeError, yaml.YAMLError):
        sys.exit("Cannot select a safe database hook from the image manifests")
