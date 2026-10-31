---
name: worldcup-analysis-zh-cn
description: >
  用于知识网络 worldcup_vega_catalog_bkn 上体育编辑、球队分析师和赛事数据管理员的世界杯历史问题：届数、主办国与冠军，
  球队与足联战绩，大名单、出场与奖项，进球与射手榜，比赛比分与决赛，红黄牌，教练与裁判，积分榜与比赛历程，点球大战与换人，球场与数据覆盖。
---

# 世界杯历史分析

回答世界杯历史数据的问题。本样例没有函数，全部用 Cypher 查询后按下面的口径计算。

## 默认口径

使用者没有另说时按以下口径回答，并在结论里简短说明用了哪条。

- 数据：男足世界杯截至 2022 年（22 届），女足截至 2019 年（8 届）；赛事编号形如 WC-2022，tournament_name 含 Women's 的是女足。明细覆盖的届次不同，没有记录不代表现实中没有发生。
- 比赛按场计数；team_appearances 每场有双方两条。出场次数按不同 match_id 计数。
- 球员进球排除乌龙球（own_goal=1）；球队进球按 goals.team_id 记账，含对方乌龙球。比赛内点球（penalty=1）算进球；点球大战罚球在 penalty_kicks，不算进球、不计入比分。
- 比分不含点球大战，点球大战比分单列；胜负平以 team_appearances 的 win、lose、draw 为准，点球大战决出的比赛通常记为平。分差是比分之差的绝对值。
- 黄牌、红牌、两黄变红、罚下各自统计，不能相加。
- 射手榜、胜场榜用竞赛排名：同分同名次、后续跳号；“前 N 名”列出名次不超过 N 的全部并列者；问“N 座、N 个”时恰好取 N 个，同值按编号排序。
- 阶段以 stage_name 为准；1950 年没有决赛，由决胜循环赛决出。联合举办的赛事每个主办国单独列出。点球大战只说罚进或未罚进。平均值保留三位小数。
- 人名、队名、奖项名用数据源英文原文；全名 = given_name + 空格 + family_name。可以附中文译名，但英文原文和编号必须写出。

## Cypher 写法

对象类型名就是标签（goals、matches、team_appearances 等），关系类型名是 rel_<来源表>_<外键>。OpenBKN 0.2.1 主线支持 WITH、CASE、聚合和 ORDER BY，不支持变长路径和 UNWIND。数值可能以字符串返回。各明细表已带赛事、阶段、球队和比赛名称，多数问题单表即可。

- 赛事：`MATCH (t:tournaments) WHERE t.tournament_id = 'WC-2022' RETURN t.year, t.start_date, t.end_date, t.host_country, t.winner`；主办国见 `host_countries`。
- 比赛与比分：`MATCH (m:matches) WHERE m.tournament_id = 'WC-2022' AND m.stage_name = 'final' RETURN m.match_id, m.match_date, m.home_team_name, m.away_team_name, m.score, m.score_penalties, m.stadium_name, m.city_name, m.country_name`
- 球员进球：`MATCH (g:goals) WHERE g.tournament_id = 'WC-2022' AND g.own_goal = 0 RETURN g.player_id, g.given_name, g.family_name, count(*) AS goals ORDER BY goals DESC`
- 球队逐场：`team_appearances` 的 `team_name`、`opponent_name`、`stage_name`、`goals_for`、`goals_against`、`penalties_for`、`penalties_against`、`win`、`lose`、`draw`。
- 出场：`player_appearances` 按 `player_id` 统计不同 `match_id`；`starter`、`substitute` 是本场首发或替补。
- 红黄牌：`bookings` 的 `yellow_card`、`red_card`、`second_yellow_card`、`sending_off` 分别求和。
- 点球大战：`penalty_kicks`（`converted`），换人：`substitutions`（`coming_on`、`going_off`、`minute_label`），按 `key_id` 数值排序即记录顺序。
- 教练与裁判：`manager_appointments`、`manager_appearances`、`referee_appearances`（`country_name`）。
- 积分与名次：`group_standings`（`group_name`、`position`、`points`）、`tournament_standings`（`position`）。
- 奖项：`award_winners`（`award_name`、`player_id`）；大名单：`squads`（`shirt_number`、`position_name`）；球场：`stadiums`（`stadium_capacity`）；足联：`teams` 经 `rel_teams_confederation` 到 `confederations`。

## 回答方式

先给结论（多少、谁、第几），再列依据：赛事、比赛、球队、球员编号和关键数字。清单和排名类问题列全，包括并列者。数据里没有记录时直接说明，不推测现实情况。
