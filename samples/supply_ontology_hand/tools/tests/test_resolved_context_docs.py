"""Docs/Skill contract for third-party handoff without legacy snapshots."""

from __future__ import annotations

from pathlib import Path

PACK = Path(__file__).resolve().parents[2]
def test_s3_no_longer_depends_on_legacy_snapshot_protocol():
    path = PACK / "skills" / "demand-fulfillment-requirement-coverage-analysis" / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    assert "run_code" not in text
    assert "resolved_context" not in text
    assert "函数服务不查询" not in text

