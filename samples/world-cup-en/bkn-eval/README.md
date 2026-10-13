# Scenario evaluation

The baseline is the locked Fjelstul snapshot. All questions describe deterministic recorded facts and explicitly define competition, grain, ties and special events where relevant.

| Category | Questions |
| --- | ---: |
| Basic queries and statistics | 10 |
| Multi-table joins | 12 |
| Rankings and cross-tournament comparisons | 14 |
| Combined business analysis | 14 |
| Total | 50 |

Run `python3 bkn-eval/scripts/recalculate.py --check` from the sample directory to verify all CSV hashes, all modeled headers and every committed reference answer. Python requires PyYAML. `gold/cases.json` contains local-only CSV reference SQL, never executed against the platform; `gold/answer-set-v1.yaml` contains the expected rows and provenance hashes. These are evaluation references, not execution instructions for a tested agent.

Give an independent agent only `datasets/question-set-v1.yaml` and access to the installed network through MCP. It may inspect published model and capability metadata, query object instances, and independently compute the requested results. Use standard network-scoped MCP object tools; do not call a runtime SQL endpoint or a platform-internal agent. Do not expose gold, CSV files or reference SQL before it finishes. Record actual tool calls and final answers locally; execution logs are not release contents.

Each question specifies `output_fields` and `row_order`. Compare every required field, entity ID and the declared ordering. Normalize numeric strings only for numeric fields; retain source names and accents. Use the set’s tolerance for rounded ratios. Include all tied ranks inside a stated boundary. Explicit zero snapshot counts are valid; unsupported conclusions about real-world participation are not.

Acceptance requires 50/50 independently correct results through MCP, plus fresh managed installation, object-query and uninstall checks. Recalculating reference answers proves baseline reproducibility, not agent accuracy. Never mark an unrun scenario as passed.
