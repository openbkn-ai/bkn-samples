"""赛事概况：一届赛事的比赛数、比分进球、场均进球、进球事件、乌龙球和点球大战罚球数。

比分进球按每场主客队比分相加，不含点球大战；场均进球保留三位小数（四舍五入）。
进球事件来自进球记录，乌龙球单独统计；点球大战罚球不计入比赛进球。
"""

from decimal import ROUND_HALF_UP, Decimal

from bkn_osdk.kn import query_object_instance, run_cypher
from sandbox_sdk import tool

KN_ID = "worldcup_vega_catalog_bkn"

MATCH_TOTALS = (
    "MATCH (m:`matches`) WHERE m.tournament_id = $t "
    "RETURN count(*) AS matches, sum(m.home_team_score) AS home, sum(m.away_team_score) AS away"
)
GOAL_TOTALS = (
    "MATCH (g:`goals`) WHERE g.tournament_id = $t "
    "RETURN count(*) AS goal_events, sum(g.own_goal) AS own_goals"
)
SHOOTOUT_KICKS = "MATCH (k:`penalty_kicks`) WHERE k.tournament_id = $t RETURN count(*) AS shootout_kicks"


def per_match(goals: int, matches: int):
    if not matches:
        return None
    return float((Decimal(goals) / Decimal(matches)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


@tool
def tournament_summary(tournament_id: str | None = None) -> dict:
    """赛事概况。tournament_id 形如 WC-2022（女足如 WC-2019 以赛事表为准）。"""
    if not tournament_id:
        raise ValueError("请提供 tournament_id，如 WC-2022")
    condition = {"field": "tournament_id", "operation": "==", "value": tournament_id, "value_from": "const"}
    found = query_object_instance(KN_ID, "tournaments", condition=condition, limit=1)["datas"]
    if not found:
        raise ValueError(f"没有找到赛事 {tournament_id}")

    params = {"t": tournament_id}
    matches = run_cypher(KN_ID, MATCH_TOTALS, parameters=params)["entries"][0]
    goals = run_cypher(KN_ID, GOAL_TOTALS, parameters=params)["entries"][0]
    kicks = run_cypher(KN_ID, SHOOTOUT_KICKS, parameters=params)["entries"][0]
    match_count = int(matches["matches"])
    match_goals = int(float(matches["home"] or 0)) + int(float(matches["away"] or 0))
    return {
        "tournament_id": tournament_id,
        "tournament_name": found[0]["tournament_name"],
        "matches": match_count,
        "match_goals": match_goals,
        "goals_per_match": per_match(match_goals, match_count),
        "goal_events": int(goals["goal_events"]),
        "own_goals": int(float(goals["own_goals"] or 0)),
        "shootout_kicks": int(kicks["shootout_kicks"]),
    }
