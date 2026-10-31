# World Cup history: tournaments, teams, players and match events PRD

## Business goal and users

Built on Joshua C. Fjelstul's open World Cup database (men's tournaments to 2022, women's to 2019), this lets users ask about World Cup history in plain business language, such as who won which edition, how a match went, who scored how many and which teams and confederations did best, and see the tournaments, matches, teams, players and events behind every answer.

| User | Questions | Expected conclusion |
|---|---|---|
| Sports editor | Tournament facts, scoring charts, awards, classic matches and star comparisons | Winners and hosts, goals and rankings, awards, how matches went |
| Team analyst | A team's run, group tables, goal breakdowns, shootouts, substitutions and discipline | Match-by-match results, positions, goal splits, kick outcomes, substitutions and cards |
| Tournament data steward | Data scope, record counts, whether records agree | Editions, matches, team and player counts, coverage per edition, scores reconciled with goal records |

Success: users get conclusions and evidence that follow these rules without stating any calculation rule in the question. An answer that is right only when the rule is spelled out in the question, and wrong when it is phrased differently, does not count.

## Data scope

In scope: tournaments, hosts, tournament stages, groups and group tables, final standings, confederations, teams, qualification, squads, players, managers and appointments, referees and appointments, stadiums, matches, team appearances, player appearances, manager appearances, referee appearances, goals, shootout kicks, bookings, substitutions, awards and winners.

Out of scope: club and non-tournament international matches; statistics the source does not hold (shots, possession, saves); guessing at missing records. Names of people, teams and awards are the source's English originals, with original spelling and accents.

## Business rules

These are the defaults, and users need not repeat them; when a user states a different condition, follow the user.

1. **Data scope**: men's World Cups to 2022 (22 editions) and women's to 2019 (8 editions). Tournament names containing Women's are women's tournaments. Detail records cover different editions; a missing record does not mean it did not happen, for example the 1999 Women's World Cup has no player-appearance records.
2. **Matches and team appearances**: matches count once each; team appearances have two rows per match (one per side). Appearances count distinct matches.
3. **Goals**: player goals exclude own goals; team goals are counted for the credited team, including opponents' own goals. In-match penalties are goals; shootout kicks are not goals and are not part of the score.
4. **Score and result**: the match score excludes the shootout, whose score is given separately. Wins, losses and draws follow the win, lose and draw flags on team appearances, never re-judged; matches decided by a shootout are normally recorded as draws. Margin is the absolute difference of the match score.
5. **Cards**: yellow cards, red cards, second yellows and sendings-off are counted separately; one booking can carry several flags, so they are never added into one total.
6. **Rankings**: scoring and win tables use competition ranking: equal values share a rank and the next rank is skipped. "Top N" returns every player or team ranked N or better, including ties at the boundary. When the question asks for a quantity such as "ten stadiums", return exactly that many, breaking ties by ID. Statistics by confederation or another category list every category, with zero where nothing is recorded.
7. **Names and identity**: full name = given name + space + family name, as in the source; people with the same name are told apart by ID.
8. **Finals and stages**: match stages follow the tournament stage records; the 1950 World Cup had no final and its winner came from a final round-robin.
9. **Hosts**: each host of a co-hosted tournament is listed separately.
10. **Shootouts**: kicks are scored or missed; never present them as goalkeeper saves.
11. **Averages**: goals per match, cards per match and similar averages use three decimals.

## Business scenarios

| Scenario | User question | Expected conclusion |
|---|---|---|
| S01 Tournament facts | How many editions, who hosted, who won | Editions, matches, hosts, winners, unusual formats |
| S02 Teams and confederations | How did teams and confederations perform | Entrants, top-scoring teams, win rankings, confederation wins |
| S03 Players, squads and awards | Who was selected, who played, who won awards | Squads, appearances, awards, star comparisons |
| S04 Goals and scorers | Who scored, how many, how | Scoring charts, goal splits, penalty goals, starter vs substitute goals |
| S05 Matches and scores | Scores of a match and of an edition | Final line-up and score, biggest wins, goals per match, scores reconciled with goal records |
| S06 Discipline | How many cards | Cards by edition and by team |
| S07 Managers and referees | Who managed, who refereed | Managers, touchline managers, referees, refereeing rankings |
| S08 Tables and team runs | How a team progressed and finished | Group tables, match-by-match runs, cross-edition comparisons |
| S09 Shootouts and substitutions | How shootouts and substitutions went | Kick order and outcome, opponent kick outcomes, substitution times |
| S10 Venues and coverage | Stadiums and data coverage | Largest stadiums, record counts per type |

## Acceptance

1. 50 questions per language covering the 10 scenarios above: 12 basic, 20 medium and 18 complex, all asked in business language without calculation rules in the question.
2. Each complex question involves at least two business rules or reasoning across three or more kinds of records.
3. Reference answers are computed by reference SQL directly from the locked CSV files, independently of the capabilities under test, and the tested side never sees them.
4. One round per language, targeting 100% accuracy.
