# Energy SAREF4ENER samples awaiting source integration

The wider sample inventory includes two developed, local unpublished energy samples
in addition to the eleven samples currently on main. They are not prototypes without
manifests: each has `sample.yaml`, data, native models, hooks, capabilities and a
0.1.3 local candidate archive. They are absent from the current main source tree,
its catalogs and the nine-package 0.2.1 prerelease batch.

## English

- Identity: `energy-saref4ener-en-us`, local version **0.1.3**.
- Scenario: demand-response eligibility, shared-capacity dispatch and metered settlement.
- Content: 15 tables, 14,787 synthetic records, 15 object types, 15 relations,
  3 functions, 2 recorded object-instance metrics and 1 investigation Skill.
- Target compatibility: `>=0.2.1 <0.3.0`, shared sample MariaDB.
- Local package SHA-256: `e2c383f016c76d62475971da521cde1295874df332bfb01ec40b7ee3b7fe79ec`.

## Chinese

- Identity: `energy-saref4ener-zh-cn`, local version **0.1.3**.
- Scenario: 需求响应资格、共享容量计划、计量交付及结算调查。
- Same declared model/data cardinalities and capabilities as the English sample.
- Target compatibility: `>=0.2.1 <0.3.0`, shared sample MariaDB.
- Local package SHA-256: `1668cfad622cbbba4bc7b3c7f6a41893500131e83940f4b1bb590de757467b02`.

## Evidence boundary and remaining work

Source and candidate archives were located in the local energy development area,
outside the active main checkout. Historical installation and question-bank evidence
also exists, including targeted corrections. It has not been independently rerun by
this update, and targeted reruns must not be combined into a new full-bank score.
The historical records distinguish install/definition checks from actual function,
metric and model calls; successful installation alone is not business acceptance.

The 0.1.3 build reports identify baseline commit
`96cea0fddf238aa6406715909faa1e37b33c6f7a` with **workingTreeChanges=true** and
`candidate-not-verified`. A baseline SHA plus dirty changes does not bind all delivered
source. These archives must not be presented as the fixed-source candidates built by
PR #198 or silently copied into its prerelease set.

For the 0.2.1 delivery, preserve and review the complete local source, upstream SAREF
references/license notices and relevant evidence, commit it, and build new immutable
candidates from that fixed source. Add the content language declaration and confirm
all required provenance files survive standard packaging. Then perform local import
and contract checks before target-product acceptance and catalog admission.

## Object Metrics V1 coverage

Each language declares two version-1 atomic `object_instance` snapshot metrics:

| Code | Meaning | Unit |
| --- | --- | --- |
| `recorded_eligible_kw` | Recorded eligible response power | kW |
| `recorded_delivery_ratio` | Recorded delivered ratio | 1 |

They must retain their event, business-date and knowledge-cutoff identity. They are
not live reconstruction or cross-date aggregates. Add their requests, unit/precision,
no-data and consumer behavior to the same V1 audit as the six mainline metric packs.
The combined developed inventory therefore has **eight metric-bearing samples and
34 metric definitions**, while the current mainline audit contains six packs and 30.
