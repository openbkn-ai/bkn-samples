from pathlib import Path

PACK = Path(__file__).resolve().parents[2]
TOOLS = PACK / "tools"
SAMPLE = PACK / "data"
KN_JSON = PACK / "kn" / "supply_ontology_en.json"


def test_pack_layout_exists():
    assert SAMPLE.is_dir()
    assert KN_JSON.is_file()
    assert (TOOLS / "requirements.txt").is_file()
    assert (TOOLS / ".gitignore").is_file()
    assert (PACK / "README.md").is_file()
    assert (TOOLS / "fn" / "__init__.py").is_file()
    assert (TOOLS / "native_function_bundle.py").is_file()
    assert (TOOLS / "register_native_function_toolbox.py").is_file()
    skills = PACK / "skills"
    assert (skills / "pmc-supply-planning" / "SKILL.md").is_file()
    assert (skills / "procurement-follow-up" / "SKILL.md").is_file()
    docs = PACK / "docs"
    assert (docs / "import-guide.en-US.md").is_file()
    assert (docs / "faq.md").is_file()
    assert (docs / "PRD.en-US.md").is_file()
    assert (TOOLS / "README.md").is_file()


def test_sample_has_fourteen_tables_and_the_plan_history():
    csvs = sorted(SAMPLE.glob("*.csv"))
    assert len(csvs) == 15
    assert (SAMPLE / "kit_schedule_plan.csv") in csvs
