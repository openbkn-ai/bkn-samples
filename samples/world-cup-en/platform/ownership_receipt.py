"""Track only execution resources created by this sample installation."""
import json
import os
from pathlib import Path


def _path():
    value = os.environ.get("BKN_SAMPLE_RECEIPT")
    return Path(value) if value else None


def read():
    path = _path()
    return json.loads(path.read_text()) if path and path.exists() else {"toolboxes": [], "skills": []}


def require_owned(kind, resource_id):
    if _path() and resource_id not in read()[kind]:
        raise RuntimeError("ownership conflict: an existing execution resource was not created by this sample")


def remember(kind, resource_id):
    path = _path()
    if not path:
        return
    receipt = read()
    if resource_id not in receipt[kind]:
        receipt[kind].append(resource_id)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt), encoding="utf-8")
    temporary.replace(path)


if __name__ == "__main__":
    import sys
    {"check": require_owned, "remember": remember}[sys.argv[1]](sys.argv[2], sys.argv[3])
