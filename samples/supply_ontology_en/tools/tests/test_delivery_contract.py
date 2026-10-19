from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


REQUIRED_FILES = (
    "README.md",
    "kn/{kn_file}",
    "data/erp_mds_forecast.csv",
    "docs/import-guide.en-US.md",
    "docs/faq.md",
    'bkn-eval/README.md',
    "bkn-eval/datasets/sample-question-set-v1.yaml",
    "bkn-eval/datasets/sample-answer-set-v1.yaml",
    "tools/import_kn.py",
    "tools/bind_kn_resources.py",
    "tools/load_sample_data.py",
    "tools/preflight.py",
    "tools/register_native_function_toolbox.py",
)


def test_english_sample_is_self_contained():
    sample = REPO_ROOT / "samples" / "supply_ontology_en"
    missing = [
        path.format(kn_file="supply_ontology_en.json")
        for path in REQUIRED_FILES
        if not (sample / path.format(kn_file="supply_ontology_en.json")).is_file()
    ]
    assert not missing, f"English sample missing delivery files: {missing}"


def test_unreleased_english_sample_is_absent():
    assert not (REPO_ROOT / "samples" / "supply_ontology_en_en").exists()


def test_english_sample_does_not_use_stage_directories():
    sample = REPO_ROOT / "samples" / "supply_ontology_en"
    assert not any(path.is_dir() for path in sample.glob("stage*"))


def test_released_sample_has_no_legacy_dataset_or_local_eval_paths():
    sample = REPO_ROOT / "samples" / "supply_ontology_en"

    assert (sample / "data" / "customer_entity.csv").is_file()
    assert not (sample / "datasets").exists()
    assert not (sample / "eval").exists()


def test_readme_explains_how_to_get_the_release_tag():
    readme = (
        REPO_ROOT / "samples" / "supply_ontology_en" / "README.md"
    ).read_text(encoding="utf-8")

    assert "supply-ontology-en-v0.1.0" in readme
    assert "git clone --branch" in readme
    assert "git fetch origin --tags --force" in readme
