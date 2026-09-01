"""Tests for offline prerequisites of the 0.1.4 onboarding path."""

from __future__ import annotations


def test_preflight_accepts_required_versions_without_platform_access():
    from preflight import run_preflight

    calls: list[list[str]] = []

    def run_local(args: list[str]) -> str:
        calls.append(args)
        return "0.1.4" if args[0] == "openbkn" else "v24.19.0"

    report = run_preflight(
        {
            "database": {
                "engine": "mysql",
                "host": "127.0.0.1",
                "port": 3306,
                "database": "supply_demo_hand",
                "user": "demo",
            },
            "vega": {"connector_options": {"sslmode": "disable"}},
        },
        run_local=run_local,
    )

    assert report["ok"] is True
    assert report["network_checked"] is False
    assert report["warnings"]
    assert calls == [["openbkn", "--version"], ["node", "--version"]]
