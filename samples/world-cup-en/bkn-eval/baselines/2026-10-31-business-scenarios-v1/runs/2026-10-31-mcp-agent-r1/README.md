# 2026-10-31 external MCP agent

An external agent answered the English 50 questions through MCP on 8081 (bkn-backend EE main 9156ec5) with sample 0.1.3 installed. The agent is the shared `mcp_agent.py` kept with the Chinese package run (it switches to English prompts for this network): the platform model deepseek-v4-flash with every tool the BKN MCP server offers; this sample has no functions, so everything is queried with Cypher. Each question opens a fresh MCP session; the answer set is never given to the agent. Answers, the round each comes from, and tool calls are in `results.json`.

Result: **50/50**.
- The first round matched 37/50 by value. A-05 lost its connection (client error), and the other misses were mostly missing record IDs and dates not written as YYYY-MM-DD.
- After the Skill added those answer requirements, the affected 13 questions were rerun. During that rerun the English package's reinstall had failed with a platform timeout, so the agent fell back to the Chinese network. That round is discarded and not counted.
- Once the package was reinstalled successfully, and the "list every category, zero where nothing is recorded" rule had been added for R-11, the same 13 questions were rerun (round 3). Every answer queried `worldcup_en`.

Reviewed by hand and correct: J-11 abbreviates CONCACAF instead of giving its full source name, and A-04 omits the team IDs while giving every scorer, minute and goal ID. All 15 experience cards also passed the online check after installation.

```bash
BKN_KN=worldcup_en python ../../../../../../world-cup/bkn-eval/baselines/2026-10-31-business-scenarios-v1/runs/2026-10-31-mcp-agent-r1/mcp_agent.py ../../question-set-v1.yaml <output-dir> --workers 4
```
