from pathlib import Path

PACK = Path(__file__).resolve().parents[2]
TOOLS = PACK / "tools"
SAMPLE = PACK / "data"
KN_JSON = PACK / "kn" / "supply_ontology_hand.json"


def test_pack_layout_exists():
    assert SAMPLE.is_dir()
    assert KN_JSON.is_file()
    assert (TOOLS / "requirements.txt").is_file()
    assert (TOOLS / ".gitignore").is_file()
    assert (PACK / "README.md").is_file()
    assert (TOOLS / "power_layer.py").is_file()
    assert (TOOLS / "fn" / "__init__.py").is_file()
    assert (TOOLS / "native_function_bundle.py").is_file()
    assert (TOOLS / "register_native_function_toolbox.py").is_file()
    skills = PACK / "skills"
    assert (skills / "production-schedule-backward-planning" / "SKILL.md").is_file()
    assert (skills / "demand-fulfillment-capacity-analysis" / "SKILL.md").is_file()
    assert (skills / "demand-fulfillment-requirement-coverage-analysis" / "SKILL.md").is_file()
    docs = PACK / "docs"
    assert (docs / "openbkn-hand-import-guide_cn.md").is_file()
    assert (docs / "faq.md").is_file()
    assert (TOOLS / "README.md").is_file()


def test_sample_has_twelve_csv():
    csvs = sorted(SAMPLE.glob("*.csv"))
    assert len(csvs) == 12
