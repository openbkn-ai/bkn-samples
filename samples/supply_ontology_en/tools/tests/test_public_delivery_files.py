from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def test_implementation_plans_are_ignored_from_public_delivery():
    rules = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "/docs/plans/" in rules
    assert "/samples/*/docs/plans/" in rules
