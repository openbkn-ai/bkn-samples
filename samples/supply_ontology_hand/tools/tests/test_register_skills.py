from __future__ import annotations


def test_register_skills_dry_run_discovers_the_local_business_skills():
    import register_skills

    result = register_skills.run(apply=False)

    assert result["mode"] == "dry_run"
    assert [item["name"] for item in result["skills"]] == [
        "demand-fulfillment-capacity-analysis",
        "demand-fulfillment-requirement-coverage-analysis",
        "demand-fulfillment-risk-summary",
        "production-schedule-backward-planning",
    ]
