# Model semantics

Object properties map directly to the locked CSV headers. Stable IDs identify entities; names are labels and may be shared by different people. `key_id` identifies a source row rather than a person or team.

| Table | Record grain |
| --- | --- |
| matches | One match |
| team_appearances | One team in one match: two records per match |
| player_appearances | One player in one match where the detail is recorded |
| squads | One player in a tournament squad |
| goals | One match-goal event, including own goals |
| penalty_kicks | One shootout kick |
| substitutions | One entering or leaving player record |
| tournament_standings | One team’s final tournament position |

Use explicit tournament IDs or the full competition name. A case-insensitive `%Men%` filter also matches Women; use `%FIFA Men''s World Cup%` for the men’s competition.

For individual scoring, exclude `own_goal=1`. For credited team scoring, use `goals.team_id`, including own goals. `player_team_id` identifies the scorer’s actual team. Match penalties are in `goals.penalty`; shootouts are in `penalty_kicks` and are excluded from match-score goals.

Booking flags can overlap. Report each requested flag separately. Preserve the dataset’s recorded win/loss/draw flags, including shootout treatment. Do not infer goalkeeper saves from unsuccessful kicks or pair unrelated simultaneous substitution rows.

Database CSV columns are stored as text. Convert numeric values before numerical comparisons or rankings; for example, compare capacities as integers rather than strings. Aggregate each fact table before joining counts, goals or bookings to prevent row multiplication.

Competition ranking uses `RANK()`: ties share a rank and the next rank skips tied positions. Include all rows within a requested rank boundary unless the question explicitly requests an exact row limit and tie-breaker.

The snapshot ends at the 2022 men’s and 2019 women’s editions. Player-appearance coverage excludes early men’s editions and WC-1999. A recorded count of zero describes this snapshot and does not establish that no player participated. WC-1950 used a final round; do not invent a knockout final.

The relationships form a minimal backbone. Additional joins must use declared fields and the correct tournament, match and entity keys.
