"""射手榜：按非乌龙球进球数给球员做竞赛排名，保留边界处的全部并列者。

可按单届赛事（tournament_id，如 WC-2022）或男足、女足（competition=men|women）筛选；
都不传时统计全部赛事。名次采用竞赛排名：并列者同名次，下一名次顺延（1、2、2、4）。
"""

from bkn_osdk.kn import query_object_instance, run_cypher
from sandbox_sdk import tool

KN_ID = "worldcup_vega_catalog_bkn"

GOALS_BY_PLAYER_AND_TOURNAMENT = (
    "MATCH (g:`goals`) WHERE g.own_goal = 0 "
    "RETURN g.player_id AS player_id, g.given_name AS given_name, g.family_name AS family_name, "
    "g.tournament_id AS tournament_id, count(*) AS goals LIMIT 10000"
)


def player_name(given_name: str, family_name: str) -> str:
    """The source marks a missing given name as 'not applicable'."""
    parts = [part for part in (given_name, family_name) if part and part != "not applicable"]
    return " ".join(parts)


def women_tournaments() -> set:
    page = query_object_instance(KN_ID, "tournaments", limit=100)
    return {row["tournament_id"] for row in page["datas"] if "Women" in row["tournament_name"]}


def competition_ranking(totals: dict, top: int) -> list:
    """totals: player_id -> goals. Rank by goals descending; ties share a rank."""
    ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    rows, rank = [], 0
    for position, (player_id, goals) in enumerate(ordered, start=1):
        if position == 1 or goals != ordered[position - 2][1]:
            rank = position
        if rank > top:
            break
        rows.append({"player_id": player_id, "goals": goals, "ranking": rank})
    return rows


@tool
def top_scorers(tournament_id: str | None = None, competition: str | None = None, top: int | None = None) -> dict:
    """射手榜。tournament_id 与 competition 二选一或都不传；top 为名次上限，默认 10。"""
    if tournament_id and competition:
        raise ValueError("tournament_id 与 competition 只能传一个")
    if competition not in (None, "men", "women"):
        raise ValueError("competition 只能是 men 或 women")
    top = 10 if top is None else int(top)
    if not 1 <= top <= 100:
        raise ValueError("top 取值范围为 1 到 100")

    rows = run_cypher(KN_ID, GOALS_BY_PLAYER_AND_TOURNAMENT)["entries"]
    if tournament_id:
        rows = [row for row in rows if row["tournament_id"] == tournament_id]
    elif competition:
        women = women_tournaments()
        rows = [row for row in rows if (row["tournament_id"] in women) == (competition == "women")]

    totals, names = {}, {}
    for row in rows:
        totals[row["player_id"]] = totals.get(row["player_id"], 0) + int(row["goals"])
        names[row["player_id"]] = player_name(row["given_name"], row["family_name"])
    ranking = competition_ranking(totals, top)
    for row in ranking:
        row["player_name"] = names[row["player_id"]]
    return {
        "scope": tournament_id or competition or "all",
        "top": top,
        "rows": ranking,
        "rule": "非乌龙球进球；竞赛排名，保留名次不超过 top 的全部并列者",
    }
