# Supply-chain component acceptance

Date: 2026-10-11. Result: candidate 0.1.3 passed fresh installation through the standard Studio APIs on the existing OpenBKN instance. It is not published in the official catalog.

## Fixed artifacts

- Sample source: `0d2468d`; package SHA256 `656f4482b734914bad87b4d86e4720ce88a9f9a4d19563a0eb6b0fccbf02b7cd`.
- Rebuilding from that clean commit reproduced the exact package installed in acceptance.
- Official sample-service Chart: `0.1.0-main.20261011041929.sha246fa25`, using the automatically detected platform version and standard API defaults.
- Exact image digests, installation attempt, values and checks: [acceptance record](phase6-component-acceptance.json).

## Actual results

| Component | Verification |
| --- | --- |
| Data | 12 business tables loaded; 3,497 materials, 31,423 BOM rows, 800 orders and 137 forecasts; the additional metadata table is installer-owned. |
| Knowledge network | 15 object types, 21 relation types and 11 business data bindings; object and cross-table queries passed installation smoke verification. |
| Metrics | Eight definitions and eight object logic-property bindings; all 13 metric queries matched expected values. |
| Functions | All 14 functions were newly registered, mounted and actually called through managed MCP; each returned exit code zero and the supply knowledge network as its data source. |
| Business behavior | Lead time 14 days, sellable quantity 534, substitute quantity 500, missing-material demand 240, backward-plan availability 2026-09-29 / 19 days late. |
| Skills | Four newly published, mounted Skills; their full main documents and all ten reference files matched the package through managed MCP reads. Their referenced functions were exercised. |
| Installation | All five stages succeeded; installed version 0.1.3 recorded. The earlier failed attempt and legacy 0.1.2 history remain visible. World Cup history was unchanged. |

## Problems found and fixed

The previous supply package declared `metrics: false` and never called its existing metric tools. Successful installation therefore did not prove metric import. The new hook creates metrics, binds them and requires actual metric-query and binding checks before success.

The first candidate failed verification correctly: two expected forecast values still referenced an older snapshot, and the open-forecast metric omitted the status dimension required by its query. The locked CSV independently sums to 115,922 forecast units (56,340 open + 59,582 closed), with 90 open rows. The corrected candidate declares the required dimension and uses these locked-data expectations. No platform permission rule was weakened.

## Scope and remaining work

This reused the single existing 8081 OpenBKN instance. Only disposable supply sample resources were backed up and recreated; no second platform instance was started. The official deployment entry was used for the sample service.

Browser automation was stopped by the computer-use tool while selecting the offline package. This run therefore used the same standard import and installation APIs used by Studio; it does not claim a completed homepage upload click-through. LLM-driven Skill conversations were not tested.

After this PR is reviewed and merged, rebuild from the reviewed source, confirm the digest, publish the immutable 0.1.3 artifacts and submit its catalog references through PR review. The candidate must not be advertised as a published release before that step. In-place upgrades and migrations remain unsupported. Follow [the sample development guide](SAMPLE_DEVELOPMENT_GUIDE.md) when changing data, knowledge, functions, metrics, Skills or interfaces.
