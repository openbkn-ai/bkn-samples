# 2026-10-30 external MCP agent

An external agent answered the v4 English set through MCP on 8081 (bkn-backend EE main 9156ec5) with sample 0.1.11 installed, so it could call the sample's functions. The agent is `mcp_agent.py`: the platform model deepseek-v4-flash (the same model Studio smart Q&A uses) with every tool the BKN MCP server offers. The system prompt names only the knowledge network and asks the agent to check the skills first and follow them. Each question opens a fresh MCP session; the answer set is never given to the agent. Answers and tool calls are in `results.json`.

Result: **50/50 in a single round**, with no reruns. Two answers needed a manual check:

- Q-31 is correct; the automatic check looks for the answer-set keys `P61_000351` and `U00_000151`, which are not business values.
- Q-50 wrote material codes with non-breaking hyphens (U+2011); after normalizing them every expected value is present.

Before this run, installation found two problems that only the English sample hits, both fixed in the same change: tool names must contain only word characters or Chinese (at most 50) with descriptions of at most 255 characters, and skill names are unique on the platform, so the English skills keep the `supply-en-` prefix. All 15 experience cards also passed the online check after installation.

```bash
BKN_KN=supply_ontology_en python mcp_agent.py ../../question-set-v4.yaml <output-dir> --workers 4
```
