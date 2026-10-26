# Read-only material shortage rule (#190)

The bilingual `shortage_rule` native Function extends the merged #189/#199
material-assurance model. Each toolbox now has 17 Functions. The rule reads BKN
facts with the official sandbox SDK and returns proposals and observed IDs only.
It does not write an event, create an event ID, close a demand, call an action,
contact a business system or implement a scheduler. Workshop remains the writer.

This is **sample adapter contract v1**, not a claim that the unmerged Workshop
interfaces are implemented. Foundry #2331 (event projection) and #2332 (ingress and
scheduler) remain dependencies. Nothing is applied to environment 23.

## Inputs and prerequisites

```json
{
  "event_source": {
    "object_type_id": "RESOLVED_EVENT_OBJECT_TYPE_ID",
    "product_relation_type_id": "RESOLVED_EVENT_TO_PRODUCT_RELATION_ID",
    "demand_event_type": "demand_registered",
    "shortage_event_type": "material_shortage",
    "verified_status": "verified",
    "processing_status": "processing",
    "closed_status": "closed"
  },
  "window_start": "2026-10-03T00:00:00Z",
  "window_end": "2026-10-04T00:00:00Z"
}
```

IDs must be resolved from the installed network metadata. The codes above are
**test examples**, not assumed final Workshop enum values. All seven configuration
keys are required, unknown keys are rejected and lifecycle mappings must differ.
They are trusted deployment configuration from the published App Spec, not a way
for an end user to verify an event. The output binds the normalized configuration
digest; ingress must compare it to the trusted published configuration and its own
authoritative event lifecycle. Calling the Function grants no write/verification
permission. API keys and tokens are not business inputs.

The configured event object exposes `event_id`, `event_type`, `status`,
`occurred_at`, `source`, `source_ref`, `verified_by`, `verified_at`, optional
`merged_into`, and JSON `detail`. The v1 demand detail contains explicit
`demand_qty` (positive whole kits), `demand_purpose` (`customer_delivery` or
`new_production`) and `warehouse_scope`. Missing policy is not silently inferred;
registration must freeze any default before verification. Source timestamps use
RFC3339 with timezone, or epoch **milliseconds** for typed BKN datetime values.
Window boundaries must be timezone-aware RFC3339 strings.

Product identity is resolved through the configured event→product relation with
`query_instance_subgraph`, using a one-hop path and overfetching two products to
reject ambiguity. The response must contain one connected event/product path,
matching event ID and product primary-key evidence. `detail.product_code` is not
an authority. Proposed material links are business-key references from the BOM;
ingress must resolve and authorize them before writing relations.

Use the execution factory's public proxy with the scoped **user-type** service
account Key. The SDK receives that caller's BKN token; the Function neither reads
credentials from files nor accepts a credential argument. BKN applies query
permissions. Do not use action scheduling, whose internal path lacks this token.

## Window and evaluation semantics

The half-open window is a **fixed scheduler evaluation identity**, reused for
retries; it is not a historical stock snapshot or a lower bound on demand age.

- New inputs must currently have the configured verified status, with verifier and
  verification timestamp, and be verified before `window_end`. No lower occurrence
  cutoff is used: late verification and older unprocessed demands are not lost.
- Existing verified/processing shortage events are read across creation windows.
  Only this rule ID/version, adapter configuration and implementation are eligible
  for automatic closure. A changed implementation is deferred, not reinterpreted.
- New candidates carry the evaluation window start as their rule occurrence time;
  original demand occurrence is retained separately in the input receipt. Ingress
  must preserve initial occurrence/history on retry or update.
- Re-evaluation reads the source demand again. A source that is now processing or
  closed can support closure only when its original verified receipt, inputs and
  product association still match. Pending/rejected inputs, missing sources or
  changed evidence are deferred. Closed status alone is not verification evidence.
- Closure requires fresh **full** coverage under the original event's creation
  identity/window. A later window may therefore close an older shortage. Failure
  or absence is never treated as zero demand or as successful coverage.
- An already active owned shortage for the same verified input suppresses a new
  candidate, including across windows and projection lag. Still-open IDs and fresh
  evaluation evidence are returned instead. Changed input receipts are not silently
  reused as the old request.

The model is single-demand analysis: all stock, finished goods before components,
no incoming supply and no alternates, with explicit customer/new-production
purpose. It does not allocate stock jointly across separate demand events and
never sums their coverage into a portfolio commitment. Each evaluation states
`independent_single_demand` and that cross-demand allocation is not evaluated.

## Output and write boundary

`contract_version=samples.material-shortage.v1` results contain:

- `candidates`: type, rule source reference, creation window, proposed object refs,
  verified source receipt, covered quantity, shortages, model/implementation and
  BOM/inventory evidence. The deterministic `deduplication_key` contains rule ID
  and version, network, source demand identity, product and creation window. No
  new `event_id` is minted. Workshop derives the stable ID and deduplicates writes.
- `closable_event_ids` and `closure_evidence`: only IDs read from existing eligible
  events; fresh coverage, source and existing-event preconditions accompany each.
- `evaluated_demand_ids`, `still_open_event_ids`, `deferred` and `has_deferred`:
  read/evaluation outcomes, not commands to alter lifecycle. `status=complete`
  means the read/evaluation ran to completion, not that deferred items are resolved.
- `configuration_digest`, rule implementation digest, source digests, exact input
  receipts and actual evaluation time. Live reads are not an atomic snapshot.

`requires_ingress_revalidation=true` always applies. Before any write, ingress must
revalidate the trusted rule/configuration, current source lifecycle and receipt,
existing event identity/source reference, object permissions and deduplication in
its authoritative ledger transaction. A caller-supplied report is not trusted
verification or authorization. Mark a demand consumed only after candidate
admission, matching existing shortage, or accepted no-shortage evaluation succeeds.
The Function does not perform those transitions.

Event reads use complete bounded pagination; partial/error/warning/truncation
responses, inconsistent totals, duplicate identities, incomplete product paths or
coverage errors fail the call. There are at most 50 new demands and 50 active
shortages per invocation, plus the coverage reader's 5,000-row bounds. If exceeded,
configure an authorized partitioned event view/type before scheduling; the rule
never silently returns the first batch. An exception invalidates all proposed
actions from that invocation.

## Local evidence and remaining acceptance

The design is read at bkn-docs PR #227 source
`e6651743e38dd1c3bd24f24b82560239a194b0b1`. SDK parameters and subgraph shape were
checked in bkn-foundry's official `infra/sandbox/runtime/sandbox_sdk/_bkn_tools.py`,
context-loader schema and ontology-query `ObjectSubGraph`/`PathsEntries` interfaces.
These source checks are not a deployed 0.2.1 interoperability receipt.

Tests use **synthetic events and mocked SDK calls** with locked sample CSVs. The
60-kit customer example yields coverage 43 and two shortages of 17; new production
covers 26 with shortages of 34. A hypothetical copied inventory increase validates
closure proposals. Repeat keys, source revocation/change/absence, later-window
closure, partial reads, invalid relations and dependency failures are exercised.
No actual event is registered, written or closed. Existing frozen banks and the
unavailable original eight historical #189 receipts remain untouched.

```sh
PYTHONPATH=samples/supply_ontology_hand/tools python -m pytest samples/supply_ontology_hand/tools/tests -q
PYTHONPATH=samples/supply_ontology_en/tools python -m pytest samples/supply_ontology_en/tools/tests -q
python tools/acceptance/shortage_rule.py --language zh-CN --output /tmp/shortage-rule-zh.json
python tools/acceptance/shortage_rule.py --language en-US --output /tmp/shortage-rule-en.json
```

Candidate versions: Chinese Supply Chain **0.1.11**, English **0.1.7**. Formal
catalogs and historical package assets remain unchanged. Real event capability
installation, approved status/type mappings, scoped proxy identity, registration →
rule invocation → ingress deduplication/closure and actual 0.2.1 acceptance remain
pending with #2331/#2332. #190 is not closed on the basis of these local tests.
