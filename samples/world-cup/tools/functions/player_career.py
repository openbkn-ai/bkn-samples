"""球员生涯：一名球员的参赛届数、非乌龙球进球（合计及逐届）和所获奖项。

用 player_id（如 P-14758）定位球员；也可以只给 family_name（可加 given_name），
同名多人时返回候选列表，请用 player_id 再查。参赛届数按大名单中不同赛事计数。
"""

from bkn_osdk.kn import query_object_instance, run_cypher
from sandbox_sdk import tool

KN_ID = "worldcup_vega_catalog_bkn"

SQUAD_TOURNAMENTS = (
    "MATCH (s:`squads`) WHERE s.player_id = $p "
    "RETURN s.tournament_id AS tournament_id, count(*) AS n ORDER BY tournament_id"
)
GOALS_BY_TOURNAMENT = (
    "MATCH (g:`goals`) WHERE g.player_id = $p AND g.own_goal = 0 "
    "RETURN g.tournament_id AS tournament_id, count(*) AS goals ORDER BY tournament_id"
)
AWARDS = (
    "MATCH (w:`award_winners`) WHERE w.player_id = $p "
    "RETURN w.tournament_id AS tournament_id, w.tournament_name AS tournament_name, "
    "w.award_id AS award_id, w.award_name AS award_name ORDER BY tournament_id, award_id"
)


def player_name(given_name: str, family_name: str) -> str:
    """The source marks a missing given name as 'not applicable'."""
    parts = [part for part in (given_name, family_name) if part and part != "not applicable"]
    return " ".join(parts)


def find_players(player_id, given_name, family_name) -> list:
    if player_id:
        condition = {"field": "player_id", "operation": "==", "value": player_id, "value_from": "const"}
    else:
        conditions = [{"field": "family_name", "operation": "==", "value": family_name, "value_from": "const"}]
        if given_name:
            conditions.append({"field": "given_name", "operation": "==", "value": given_name, "value_from": "const"})
        condition = conditions[0] if len(conditions) == 1 else {"operation": "and", "sub_conditions": conditions}
    return query_object_instance(KN_ID, "players", condition=condition, limit=20)["datas"]


@tool
def player_career(player_id: str | None = None, given_name: str | None = None, family_name: str | None = None) -> dict:
    """球员生涯。传 player_id，或传 family_name（可加 given_name）。"""
    if not player_id and not family_name:
        raise ValueError("请提供 player_id，或 family_name（可加 given_name）")
    players = find_players(player_id, given_name, family_name)
    if not players:
        raise ValueError("没有找到该球员")
    if len(players) > 1:
        return {
            "ambiguous": True,
            "candidates": [
                {"player_id": row["player_id"], "player_name": player_name(row["given_name"], row["family_name"]),
                 "birth_date": row.get("birth_date"), "female": row.get("female")}
                for row in players
            ],
        }

    player = players[0]
    params = {"p": player["player_id"]}
    tournaments = [row["tournament_id"] for row in run_cypher(KN_ID, SQUAD_TOURNAMENTS, parameters=params)["entries"]]
    goals = [{"tournament_id": row["tournament_id"], "goals": int(row["goals"])}
             for row in run_cypher(KN_ID, GOALS_BY_TOURNAMENT, parameters=params)["entries"]]
    awards = run_cypher(KN_ID, AWARDS, parameters=params)["entries"]
    return {
        "player_id": player["player_id"],
        "player_name": player_name(player["given_name"], player["family_name"]),
        "editions": len(tournaments),
        "tournaments": tournaments,
        "goals": sum(row["goals"] for row in goals),
        "goals_by_tournament": goals,
        "awards": awards,
        "rule": "届数按大名单中不同赛事计数；进球不含乌龙球",
    }
