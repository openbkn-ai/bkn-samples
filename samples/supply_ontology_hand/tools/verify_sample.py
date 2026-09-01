#!/usr/bin/env python3
"""Read-only release verifier for the public experience pack."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


def verify_bkn_eval(root: Path) -> dict[str, Any]:
    datasets = root / "bkn-eval" / "datasets"
    questions = yaml.safe_load(
        (datasets / "sample-question-set-v1.yaml").read_text(encoding="utf-8")
    )
    answers = yaml.safe_load(
        (datasets / "sample-answer-set-v1.yaml").read_text(encoding="utf-8")
    )
    question_ids = {item["id"] for item in questions["questions"]}
    answer_ids = {item["id"] for item in answers["answers"]}
    return {
        "passed": len(question_ids) == 50 and question_ids == answer_ids,
        "question_count": len(question_ids),
        "answer_count": len(answer_ids),
    }


def verify(pack: str | Path, *, run_tests: bool = True) -> dict[str, Any]:
    root = Path(pack)
    required = [
        root / "README.md",
        root / "docs/openbkn-hand-import-guide_cn.md",
        root / "docs/faq.md",
        root / "bkn-eval/体验评测指南.md",
        root / "tools/preflight.py",
        root / "tools/register_native_function_toolbox.py",
        root / "tools/register_skills.py",
        root / "tools/fn",
        root / "tools/assets/metrics-create.json",
    ]
    documentation_passed = all(path.exists() for path in required)
    test_process = None
    if run_tests:
        test_process = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "--disable-warnings"], cwd=root / "tools", capture_output=True, text=True, check=False)
    evaluation = verify_bkn_eval(root)
    tests_passed = None if test_process is None else test_process.returncode == 0
    passed = documentation_passed and evaluation["passed"] and (tests_passed is None or tests_passed)
    return {"passed": passed, "documentation_passed": documentation_passed, "tests_passed": tests_passed, "test_output": "" if test_process is None else test_process.stdout[-1000:], "evaluation": evaluation}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    report = verify(root)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    raise SystemExit(0 if report["passed"] else 1)
