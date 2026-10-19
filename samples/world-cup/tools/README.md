# World Cup functions

The installer publishes the native functions in `functions/` through `register_functions.py` and mounts them to the knowledge network. Each file is one self-contained Function: it reads the network through the sandbox's preinstalled `bkn_osdk` (`run_cypher`, `query_object_instance`), with the gateway and credentials supplied by the runtime.

| Function | File | Answers |
| --- | --- | --- |
| 射手榜 | `functions/top_scorers.py` | Competition ranking by non-own goals for one tournament, men, women or all |
| 球员生涯 | `functions/player_career.py` | Editions, goals per tournament and awards for one player |
| 赛事概况 | `functions/tournament_summary.py` | Matches, match goals, goals per match, own goals and shoot-out kicks for one tournament |

Agents can still query objects directly through `query_object_instance` and `run_cypher`. Offline checks run the published files against the embedded CSV files:

```sh
python -m pytest tools/tests -q
```
