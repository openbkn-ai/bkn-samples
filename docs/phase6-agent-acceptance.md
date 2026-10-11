# Model-driven business Skill acceptance

2026-10-11. A child agent used the configured deepseek-v4-flash model through OpenBKN Model Factory and SDK managed MCP. The model autonomously searched and read the four installed supply business Skills and called their business functions. No creator Skills or business writes were used. This is MCP/model acceptance, not a claim that browser chat interaction was tested.

| Case | Actual verified result |
| --- | --- |
| Sellable stock | 534 available; demand 100; 434 remaining |
| Backward plan | 2026-09-29 available; customer 19 days late; internal maximum delay 25 days; material 321-000569 shortage 240 |
| Substitute | Material 356-000356 available 500; ten groups refer to the same stock, not 5,000 |
| Capacity | Finished stock 534; theoretical build zero; total 534; bottleneck 725-000105 |

All four final cases passed and managed MCP receipts completed. The substitute harness initially reused invocation identity and received terminal receipts; distinct invocation IDs resolved the test harness issue. Raw failed evidence was retained locally, not counted as success. [Concise JSON evidence](phase6-agent-acceptance.json) records the actual model, values, tool names and receipt status. [Component acceptance](phase6-component-acceptance.md) separately covers all 14 function calls and 13 metric query cases.
