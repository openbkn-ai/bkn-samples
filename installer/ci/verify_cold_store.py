"""Validate compressed content in a fresh Docker/containerd store after a pull.

Only manifest/config JSON is copied out. Layer hashes are computed inside the
harness so the evidence does not duplicate the image or contain Docker auth.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def verify(container, directory, index_digest, architecture):
    directory = Path(directory)
    blobs = {}
    for line in (directory / "blob-hashes.txt").read_text().splitlines():
        actual, path = line.split(maxsplit=1)
        expected = Path(path).name
        if actual != expected or len(actual) != 64:
            raise ValueError("content blob hash does not match its address")
        blobs["sha256:" + actual] = path

    def read_json(digest, name):
        raw = subprocess.check_output(["docker", "exec", container, "cat", blobs[digest]])
        if "sha256:" + hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("metadata content digest mismatch")
        (directory / name).write_bytes(raw)
        return json.loads(raw)

    index = read_json(index_digest, "index.json")
    matches = [m for m in index["manifests"]
               if m.get("platform", {}).get("os") == "linux"
               and m["platform"].get("architecture") == architecture]
    if len(matches) != 1:
        raise ValueError("expected exactly one manifest for the native platform")
    manifest = read_json(matches[0]["digest"], "platform-manifest.json")
    config = read_json(manifest["config"]["digest"], "config.json")
    if config.get("architecture") != architecture or config.get("os") != "linux":
        raise ValueError("image config architecture does not match native runner")
    layers = []
    for layer in manifest["layers"]:
        if layer["digest"] not in blobs:
            raise ValueError("compressed layer content missing from fresh store")
        size = int(subprocess.check_output([
            "docker", "exec", container, "stat", "-c", "%s", blobs[layer["digest"]]
        ]))
        if size != layer["size"]:
            raise ValueError("compressed layer size mismatch")
        layers.append({"digest": layer["digest"], "size": size, "sha256_verified": True})
    result = {"index_digest": index_digest, "manifest_digest": matches[0]["digest"],
              "config_digest": manifest["config"]["digest"], "architecture": architecture,
              "layers": layers, "passed": True}
    (directory / "verification.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    verify(*sys.argv[1:])
