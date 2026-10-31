# 2026-10-30 external MCP agent

An external agent answered the English 50 questions through MCP on 8081 (bkn-backend EE main 9156ec5) with sample 0.1.6 installed, so it could call the sample's functions. The agent is `mcp_agent.py`: the platform model deepseek-v4-flash (the same model Studio smart Q&A uses) with every tool the BKN MCP server offers. The system prompt names only the knowledge network and asks the agent to check the skills first and follow them. Each question opens a fresh MCP session; the answer set is never given to the agent. Answers, the round each comes from, and tool calls are in `results.json`.

Result: **50/50**. The first round scored 49/50: Q-45 treated the commitment behind the withdrawn offer as void, while the business rule keeps committed allocations in full and only makes the block's new plan undeterminable.

The fix states in the network description and Skills that a withdrawn offer never cancels a commitment, and that `event_ids` takes up to 20 events per call rather than one block at a time; that batching guidance came from the Chinese run, which ran out of its per-interaction operation budget. After reinstalling, only the affected Q-42, Q-45 and Q-50 were rerun (round 2), and all three were answered correctly. A third round reran Q-42 and Q-46 after the Skills told snapshot checks to recompute 20 events at a time dated 2027-02-28; both were correct. The other 45 questions keep their first-round answers.

The automatic check treats the mathematical minus sign (U+2212) in answers as a hyphen-minus. Reviewed by hand and correct:
- Q-11 states the reason in words (the latest forecast is invalid, with no fallback).
- Q-34 writes the net as −CNY 6.51.
- Q-28 gives both verified energies, 52.5 and 46.5 kWh, and describes the corrected reading as revision 2 rather than naming its ID.

All 15 experience cards also passed the online check after installation.

```bash
BKN_KN=energy_saref4ener_en_us python mcp_agent.py ../../question-set-v1.yaml <output-dir> --workers 4
```
