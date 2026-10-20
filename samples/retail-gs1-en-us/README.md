# Food Supply Chain Traceability and Recall

Synthetic receipt inspection, warehouse/store movements, sales/returns, expiry/reservations, shared-stock fulfillment, future replenishment and recall. Requires OpenBKN >=0.2.1 <0.3.0.

Import the offline archive from the homepage, install and open the network. This is an unpublished local candidate; installation and one-pass Q&A acceptance are recorded separately in verification evidence, not assumed here. English and Chinese are separate samples.

[PRD](docs/PRD.en-US.md) · [Business contract](docs/business-contract.md) · [BKN ontology](docs/ontology.md) · [GS1 sources/license](docs/standard-sources.md).

15 populated object types, 30 foreign-key relations, 3 concept groups; three functions, two recorded snapshot metrics and one investigation Skill. Default observation 2027-02-28; data spans November 2026 through March 2027. Unknown is not zero; planned supply is not realized stock. No business action is executed.

100 questions per language, 30 basic/40 medium/30 complex, mapped to the PRD's 10 scenarios. Questions/gold are development-only, excluded from runtime archives. After deterministic checks, run one formal subagent Q&A pass, preserving first failures; 100% is a target and results are reported as observed.

2026-10-20 original full-pass result: English 96/100, Chinese 95/100; original scores are retained. The repaired candidates were subsequently installed on 8081 under explicit authorization. Only the prior nonpassing cases were retested: English 4/4 and Chinese 5/5 passed, all execution and evidence states complete. The duplicate-event repair is effective on live data, and question/output contracts were clarified. No second full-bank run was performed; this does not establish 100% on the complete revised banks. [Original acceptance](verification/acceptance-20261020.json) · [Targeted retest](verification/targeted-retest-20261020.json) · [Detailed analysis](../../docs/retail-gs1-acceptance.en-US.md).
