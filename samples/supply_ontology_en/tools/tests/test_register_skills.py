from __future__ import annotations


def test_register_skills_dry_run_discovers_the_local_business_skills():
    import register_skills

    result = register_skills.run(apply=False)

    assert result["mode"] == "dry_run"
    assert [item["name"] for item in result["skills"]] == [
        "supply-en-demand-fulfillment-capacity-analysis",
        "supply-en-demand-fulfillment-requirement-coverage-analysis",
        "supply-en-demand-fulfillment-risk-summary",
        "supply-en-production-schedule-backward-planning",
        "supply-en-sales-signing-calendar-month-analysis",
    ]
