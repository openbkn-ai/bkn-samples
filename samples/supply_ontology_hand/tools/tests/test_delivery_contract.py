from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


REQUIRED_FILES = (
    "README.md",
    "kn/{kn_file}",
    "data/erp_mds_forecast.csv",
    "docs/openbkn-hand-import-guide_cn.md",
    "docs/faq.md",
    "bkn-eval/体验评测指南.md",
    "bkn-eval/datasets/sample-question-set-v1.yaml",
    "bkn-eval/datasets/sample-answer-set-v1.yaml",
    "tools/import_kn.py",
    "tools/bind_kn_resources.py",
    "tools/load_sample_data.py",
    "tools/preflight.py",
    "tools/register_native_function_toolbox.py",
    "tools/register_skills.py",
)


def test_chinese_sample_is_self_contained():
    sample = REPO_ROOT / "samples" / "supply_ontology_hand"
    missing = [
        path.format(kn_file="supply_ontology_hand.json")
        for path in REQUIRED_FILES
        if not (sample / path.format(kn_file="supply_ontology_hand.json")).is_file()
    ]
    assert not missing, f"Chinese sample missing delivery files: {missing}"


def test_unreleased_english_sample_is_absent():
    assert not (REPO_ROOT / "samples" / "supply_ontology_hand_en").exists()


def test_chinese_sample_does_not_use_stage_directories():
    sample = REPO_ROOT / "samples" / "supply_ontology_hand"
    assert not any(path.is_dir() for path in sample.glob("stage*"))


def test_released_sample_has_no_legacy_dataset_or_local_eval_paths():
    sample = REPO_ROOT / "samples" / "supply_ontology_hand"

    assert (sample / "data" / "customer_entity.csv").is_file()
    assert not (sample / "datasets").exists()
    assert not (sample / "eval").exists()
