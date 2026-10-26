# Material assurance follow-up (#189)

This source update adds bilingual `material_coverage` and `replenishment_draft`
Functions to the existing native toolbox (16 Functions in total), plus a draft-only
BKN action that binds to the latter. It does not change data, immutable metric
definitions, the formal catalog or a live knowledge network.

## Rules and result contract

| Input purpose | Finished goods | Locked CSV, demand 60 | Two material gaps |
| --- | --- | --- | --- |
| `customer_delivery` | Allocate first | Covers 43: 17 finished + 26 manufacturing | 17 each |
| `new_production` | Excluded | Covers 26 | 34 each |

`product`, positive whole-kit `qty` and explicit `demand_purpose` are required.
`warehouse_scope` defaults to `all`; the native entrypoint also supports the existing
`production_available` and `finished_goods` presets. No incoming supply or alternates
are consumed. Every manufacturing level allocates its available component stock
before expanding the residual; repeated positions share one request-local pool.
These business inputs belong to `material_coverage`; the draft Function accepts
its complete result rather than re-reading facts.
Coverage is bounded by the requested quantity, separate from unlimited theoretical
capacity. Each gap has its material identity and position evidence; quantities for
different materials are not added together.

Replacement classification uses the fields **together**:

| Method | Group | Priority | Meaning |
| --- | --- | --- | --- |
| Empty, or legacy explicit primary label | Empty/0 | 0 | Ordinary main |
| `替代` / `Alternate` | Present | 0 | Replacement-group main |
| `替代` / `Alternate` | Present | Positive integer | Replacement candidate |
| Empty/legacy primary label | Present | 0 | Legacy group-main representation |

Missing priorities in a replacement group, unknown methods, negative/fractional
priorities, or a positive priority without replacement method/group fail explicitly.
Assurance also rejects a candidate without a main in the same parent/group.
The same classifier drives BOM filters, allocation and native fact acquisition.
The actual export labels **both** the group main and its alternatives with the
replacement method; filtering every row with that method would discard valid mains.
For product `623-000034`, all 549 BOM rows are read, including 439 priority-zero
mains (347 ordinary + 92 group mains). The legacy empty-method filter returned
347 rows; that is a different subset, not the complete BOM.

Results record source BOM version `2026-08-05`, full BOM row count, BOM/inventory
content digests and collection timestamps. The native wrapper records read-start
and read-completion times. Live reads do not constitute an atomic database snapshot.
Bounded pagination follows short pages with continuations or an outstanding total;
partial responses, inconsistent totals, repeated rows/cursors and safety-bound
exhaustion fail rather than becoming a partial success.

## Draft-only action

`<kn>_act_replenishment_draft` calls the new draft Function with one `coverage` object
from the prior material-assurance calculation. It validates the supplied structure,
not the underlying facts, and returns a `draft_id`, item quantities,
source coverage, `status=draft`, `persisted=false`, `executable=false`, and
`basis_validation=structure_only_not_requeried`. This pure conversion performs no
BKN reads, so it also works on the internal action path without `BKN_TOKEN`.
Workshop must bind the supplied evidence to its actual calculation run; a caller
provided object is not independently verified business truth.
Identical facts and inputs produce the same draft identity; a collection timestamp
alone does not create a new identity. Supplier, delivery date, production capacity,
cost, MOQ and safety stock remain unresolved. The action's `add` intent describes
creating a proposal; it has no declared business-object effect, persistent draft
store, procurement endpoint or schedule.

During candidate installation, registration binds only an owned sample network and
matching local draft-action definition. An already matching binding is reused;
another tool binding is rejected. Platform verification checks both mounted
Functions and the draft-action binding, without executing the action.
Only local source definitions are changed in this PR. Nothing is applied to the
existing environment 23. Draft storage and workflow integration remain Workshop work.

## Evidence and remaining acceptance

The design is read at bkn-docs PR #227 source commit
`e6651743e38dd1c3bd24f24b82560239a194b0b1`; it is draft/unmerged design, not a
released platform interface. Sample source follows existing BKN/Function contracts.

The original `bkn-decision-design-scenario-replay-20261007.json` and
`supply-stock-demo.independent-20261003.json` are no longer on this machine, as
confirmed by the user. Their eight original cases cannot yet be reconciled.
The eight **new** local regression cases cover both purposes under unchanged stock,
manual-only +17, both materials +17 and both +34. They are not original receipts,
a new Agent score or Scenario platform acceptance. Existing frozen evaluation banks
are retained; new questions/answers live in separate material-assurance banks.

Reproduce from repository root (pytest is a test dependency only):

```sh
PYTHONPATH=samples/supply_ontology_hand/tools python -m pytest samples/supply_ontology_hand/tools/tests -q
PYTHONPATH=samples/supply_ontology_en/tools python -m pytest samples/supply_ontology_en/tools/tests -q
python tools/acceptance/material_assurance.py --language zh-CN --output /tmp/material-assurance-zh.json
python tools/acceptance/material_assurance.py --language en-US --output /tmp/material-assurance-en.json
```

Source/candidate versions: Supply Chain Chinese **0.1.10**, English **0.1.5**.
They remain outside the formal catalog. Actual 0.2.1 native Function and action
query/execution receipts, target permissions, Workshop integration and original
historical replay reconciliation remain pending; #189 is not closed by local tests.
#190 can consume this result contract, but event registration/projection and rule
scheduling remain dependent on Foundry #2331/#2332.
