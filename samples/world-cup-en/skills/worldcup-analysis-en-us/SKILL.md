---
name: worldcup-analysis-en-us
description: >
  Use for World Cup history questions from sports editors, team analysts and data stewards on knowledge network worldcup_en:
  editions, hosts and winners, team and confederation records, squads, appearances and awards, goals and scoring charts,
  scores and finals, cards, managers and referees, tables and team runs, shootouts and substitutions, stadiums and coverage.
---

# World Cup history analysis

Answer questions about the World Cup history data. This sample has no functions; query with Cypher and apply the rules below.

## Default rules

Unless the user says otherwise, answer with these rules and name the rule you used in one short phrase.

- Data: men's World Cups to 2022 (22 editions) and women's to 2019 (8 editions); tournament IDs look like WC-2022, and a tournament_name containing Women's is a women's tournament. Detail records cover different editions; a missing record does not mean it did not happen.
- Matches count once each; team_appearances has two rows per match. Appearances count distinct match_id values.
- Player goals exclude own goals (own_goal=1); team goals are credited by goals.team_id, including opponents' own goals. In-match penalties (penalty=1) are goals; shootout kicks are in penalty_kicks, are not goals and are not part of the score.
- The score excludes the shootout, whose score is separate; wins, losses and draws follow win, lose and draw on team_appearances, and shootout-decided matches are normally draws. Margin is the absolute score difference.
- Yellow cards, red cards, second yellows and sendings-off are counted separately, never added up.
- Scoring and win tables use competition ranking: equal values share a rank and the next rank is skipped; "top N" lists everyone ranked N or better, including ties; a request for a quantity such as "ten stadiums" returns exactly that many, ties broken by ID.
- Stages follow stage_name; 1950 had no final and was decided by a final round. Each co-host is listed separately. Shootout kicks are scored or missed. Averages use three decimals.
- Use the source's names; full name = given_name + space + family_name, and always include IDs.

## Cypher patterns

Object type IDs are the labels (worldcup_en_goals, worldcup_en_matches, worldcup_en_team_appearances and so on); relation types are wc_en_rel_<source>_<key>. The OpenBKN 0.2.1 mainline supports WITH, CASE, aggregation and ORDER BY, not variable-length paths or UNWIND. Numbers may come back as strings. Detail tables already carry tournament, stage, team and match names, so most questions need one table.

- Tournament: `MATCH (t:worldcup_en_tournaments) WHERE t.tournament_id = 'WC-2022' RETURN t.year, t.start_date, t.end_date, t.host_country, t.winner`; hosts are in `worldcup_en_host_countries`.
- Matches and scores: `MATCH (m:worldcup_en_matches) WHERE m.tournament_id = 'WC-2022' AND m.stage_name = 'final' RETURN m.match_id, m.match_date, m.home_team_name, m.away_team_name, m.score, m.score_penalties, m.stadium_name, m.city_name, m.country_name`
- Player goals: `MATCH (g:worldcup_en_goals) WHERE g.tournament_id = 'WC-2022' AND g.own_goal = 0 RETURN g.player_id, g.given_name, g.family_name, count(*) AS goals ORDER BY goals DESC`
- Team runs: `worldcup_en_team_appearances` with `team_name`, `opponent_name`, `stage_name`, `goals_for`, `goals_against`, `penalties_for`, `penalties_against`, `win`, `lose`, `draw`.
- Appearances: count distinct `match_id` per `player_id` in `worldcup_en_player_appearances`; `starter` and `substitute` mark the player's role in that match.
- Cards: sum `yellow_card`, `red_card`, `second_yellow_card` and `sending_off` in `worldcup_en_bookings` separately.
- Shootouts: `worldcup_en_penalty_kicks` (`converted`); substitutions: `worldcup_en_substitutions` (`coming_on`, `going_off`, `minute_label`); numeric `key_id` order is the record order.
- Managers and referees: `worldcup_en_manager_appointments`, `worldcup_en_manager_appearances`, `worldcup_en_referee_appearances` (`country_name`).
- Tables and positions: `worldcup_en_group_standings` (`group_name`, `position`, `points`), `worldcup_en_tournament_standings` (`position`).
- Awards: `worldcup_en_award_winners` (`award_name`, `player_id`); squads: `worldcup_en_squads` (`shirt_number`, `position_name`); stadiums: `worldcup_en_stadiums` (`stadium_capacity`); confederations: `worldcup_en_teams` through `wc_en_rel_teams_confederation`.

## How to answer

Lead with the conclusion (how many, who, which rank), then the basis: tournament, match, team and player IDs and the key figures. List every item in list and ranking questions, including ties. When the data holds no record, say so; never guess at real-world events.
