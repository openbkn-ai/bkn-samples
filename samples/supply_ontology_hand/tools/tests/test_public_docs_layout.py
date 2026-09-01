from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[2]
DOCS = PACKAGE / "docs"


def test_public_docs_have_one_short_entry_path():
    public_markdown = {
        path.relative_to(DOCS).as_posix()
        for path in DOCS.rglob("*.md")
    }

    assert public_markdown == {
        "faq.md",
        "openbkn-hand-import-guide_cn.md",
        "reference/capability-contract.md",
    }
    assert not (DOCS / "payloads").exists()
    assert not (DOCS / "catalog").exists()
    assert not (DOCS / "playbook").exists()
    assert not (DOCS / "quickstart").exists()
