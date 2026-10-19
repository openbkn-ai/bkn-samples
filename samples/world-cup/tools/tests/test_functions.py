"""World Cup native functions: readable single files, checked against the frozen answers.

The fake bkn_osdk answers each Cypher statement the functions issue from the
embedded CSV files, so the calculations run offline exactly as published.
"""
import ast
import csv
import importlib.util
import sys
import types
from collections import Counter
from pathlib import Path

import pytest

SAMPLE = Path(__file__).resolve().parents[2]
FUNCTIONS = SAMPLE / "tools" / "functions"
OPERATIONS = ("top_scorers", "player_career", "tournament_summary")
RUNTIME_PREFIX = "import sys\nimport json\nimport traceback\nimport sandbox_sdk\n\n"


def rows(table):
    with (SAMPLE / "data" / f"{table}.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def matches(row, condition):
    if condition.get("operation") == "and":
        return all(matches(row, item) for item in condition["sub_conditions"])
    assert condition["operation"] == "=="
    return row.get(condition["field"]) == condition["value"]


def query_object_instance(kn_id, ot_id, condition=None, limit=None, **_):
    data = [row for row in rows(ot_id) if not condition or matches(row, condition)]
    return {"datas": data[:limit] if limit else data}


def run_cypher(kn_id, query, parameters=None, **_):
    p = (parameters or {}).get("p")
    t = (parameters or {}).get("t")
    if "MATCH (g:`goals`) WHERE g.own_goal = 0 RETURN" in query:
        counts = Counter((r["player_id"], r["given_name"], r["family_name"], r["tournament_id"])
                         for r in rows("goals") if r["own_goal"] == "0")
        return {"entries": [{"player_id": k[0], "given_name": k[1], "family_name": k[2], "tournament_id": k[3], "goals": n}
                            for k, n in counts.items()]}
    if "MATCH (s:`squads`)" in query:
        counts = Counter(r["tournament_id"] for r in rows("squads") if r["player_id"] == p)
        return {"entries": [{"tournament_id": k, "n": n} for k, n in sorted(counts.items())]}
    if "MATCH (g:`goals`) WHERE g.player_id = $p" in query:
        counts = Counter(r["tournament_id"] for r in rows("goals") if r["player_id"] == p and r["own_goal"] == "0")
        return {"entries": [{"tournament_id": k, "goals": n} for k, n in sorted(counts.items())]}
    if "MATCH (w:`award_winners`)" in query:
        found = sorted((r for r in rows("award_winners") if r["player_id"] == p), key=lambda r: (r["tournament_id"], r["award_id"]))
        return {"entries": [{k: r[k] for k in ("tournament_id", "tournament_name", "award_id", "award_name")} for r in found]}
    if "MATCH (m:`matches`)" in query:
        found = [r for r in rows("matches") if r["tournament_id"] == t]
        return {"entries": [{"matches": len(found), "home": sum(int(r["home_team_score"]) for r in found),
                             "away": sum(int(r["away_team_score"]) for r in found)}]}
    if "MATCH (g:`goals`) WHERE g.tournament_id = $t" in query:
        found = [r for r in rows("goals") if r["tournament_id"] == t]
        return {"entries": [{"goal_events": len(found), "own_goals": sum(int(r["own_goal"]) for r in found)}]}
    if "MATCH (k:`penalty_kicks`)" in query:
        return {"entries": [{"shootout_kicks": sum(r["tournament_id"] == t for r in rows("penalty_kicks"))}]}
    raise AssertionError(f"unexpected query: {query}")


@pytest.fixture
def published(monkeypatch):
    sdk = types.ModuleType("sandbox_sdk")
    sdk.tool = lambda func: func
    osdk = types.ModuleType("bkn_osdk")
    kn = types.ModuleType("bkn_osdk.kn")
    kn.query_object_instance = query_object_instance
    kn.run_cypher = run_cypher
    osdk.kn = kn
    for name, module in (("sandbox_sdk", sdk), ("bkn_osdk", osdk), ("bkn_osdk.kn", kn)):
        monkeypatch.setitem(sys.modules, name, module)

    def load(operation):
        # Same shape as the runtime: its imports first, then the code, as __main__.
        namespace = {"__name__": "__main__"}
        source = (FUNCTIONS / f"{operation}.py").read_text(encoding="utf-8")
        exec(compile(RUNTIME_PREFIX + source, operation, "exec"), namespace)
        return namespace[operation]
    return load


@pytest.mark.parametrize("operation", OPERATIONS)
def test_each_function_is_one_readable_file_with_one_sdk_entry(operation):
    source = (FUNCTIONS / f"{operation}.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    entries = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)
               and any(isinstance(d, ast.Name) and d.id == "tool" for d in node.decorator_list)]
    assert entries == [operation]
    assert "__future__" not in source
    assert "http://" not in source and "https://" not in source
    assert "from bkn_osdk.kn import" in source


def test_registered_inputs_match_the_function_signatures():
    spec = importlib.util.spec_from_file_location("register_functions", SAMPLE / "tools/register_functions.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for operation, entry in module.FUNCTIONS.items():
        tree = ast.parse((FUNCTIONS / f"{operation}.py").read_text(encoding="utf-8"))
        func = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == operation)
        assert [arg.arg for arg in func.args.args] == [item["name"] for item in entry["inputs"]]


def test_top_scorers_match_frozen_rankings(published):
    top_scorers = published("top_scorers")
    wc2022 = top_scorers(tournament_id="WC-2022", top=5)["rows"]
    assert [(r["player_id"], r["goals"], r["ranking"]) for r in wc2022][:4] == [
        ("P-64077", 8, 1), ("P-14758", 7, 2), ("P-19776", 4, 3), ("P-89750", 4, 3)]
    assert len(wc2022) == 11 and {r["ranking"] for r in wc2022[4:]} == {5}
    men = top_scorers(competition="men")["rows"]
    assert (men[0]["player_id"], men[0]["goals"], len(men)) == ("P-27787", 16, 15)
    women = top_scorers(competition="women")["rows"]
    assert [(r["player_id"], r["goals"], r["ranking"]) for r in women[:3]] == [
        ("P-07458", 17, 1), ("P-52478", 14, 2), ("P-89236", 14, 2)]
    assert len(women) == 11


def test_player_career_matches_frozen_answers(published):
    player_career = published("player_career")
    thomas = player_career(player_id="P-28154")
    gerd = player_career(player_id="P-72441")
    assert (thomas["player_name"], thomas["editions"], thomas["goals"]) == ("Thomas Müller", 4, 10)
    assert (gerd["player_name"], gerd["editions"], gerd["goals"]) == ("Gerd Müller", 2, 14)
    messi = player_career(player_id="P-14758")
    assert messi["goals_by_tournament"] == [
        {"tournament_id": "WC-2006", "goals": 1}, {"tournament_id": "WC-2014", "goals": 4},
        {"tournament_id": "WC-2018", "goals": 1}, {"tournament_id": "WC-2022", "goals": 7}]
    assert [(a["tournament_id"], a["award_name"]) for a in messi["awards"] if a["tournament_id"] in ("WC-2014", "WC-2022")] == [
        ("WC-2014", "Golden Ball"), ("WC-2022", "Golden Ball"), ("WC-2022", "Silver Boot")]
    assert player_career(family_name="Müller")["ambiguous"] is True


@pytest.mark.parametrize("tournament_id, expected", [
    ("WC-2014", {"matches": 64, "match_goals": 171, "goals_per_match": 2.672, "goal_events": 171, "own_goals": 5, "shootout_kicks": 36}),
    ("WC-2018", {"matches": 64, "match_goals": 169, "goals_per_match": 2.641, "goal_events": 169, "own_goals": 12, "shootout_kicks": 39}),
    ("WC-2022", {"matches": 64, "match_goals": 172, "goals_per_match": 2.688, "goal_events": 172, "own_goals": 2, "shootout_kicks": 41}),
])
def test_tournament_summary_matches_frozen_answers(published, tournament_id, expected):
    result = published("tournament_summary")(tournament_id=tournament_id)
    assert {key: result[key] for key in expected} == expected
