# BKN modeling specification: financial FIBO sample

## Purpose

This specification translates the approved business scope and FIBO mappings into native BKN resources. It is the contract used before data, evaluator, and installer implementation.

## Resource rules

1. Every importable table becomes one named BKN ObjectType. Object keys are stable fictional business identifiers; label fields are human-readable and localizable.
2. Every cross-object business fact required by a P0 decision becomes one named BKN RelationType with explicit source and target ObjectTypes. Foreign-key fields remain in the data and map one-to-one to the relationship endpoint.
3. BKN IDs and display names must meet platform limits: ASCII lower-snake-case IDs, stable filename equal to the relation ID, and no `id` or `name` longer than 40 characters.
4. Direct FIBO mappings include `source_iri`, `source_label`, `source_definition`, `source_repository`, `source_revision`, and `source_license`. Extensions include `semantic_anchor_iri` or a written local definition.
5. `as_of_date`, `effective_from_date`, `effective_to_date`, `trade_date`, and `settlement_date` are date-only. A conclusion must name the date it relies on.
6. Status is an explicit controlled value, never inferred from the absence of a record. Settlement and valuation exceptions preserve their reason and source record.
7. Amounts retain value, currency, basis, and as-of date. A derived exposure retains its contributing valuation IDs and aggregation rule.

## Model layers

| Layer | Content | BKN use |
|---|---|---|
| FIBO reference layer | Source concepts, definitions, source IRIs, and property inventory | Provenance and modeling guidance; not operational instance data. |
| Financial operations layer | Instrument, entity, portfolio, trade, settlement, position, price, valuation, exposure, and mandate objects | Installed ObjectTypes and direct RelationTypes. |
| Decision layer | Limit assessments and explicit exception states | Installed operational objects; only add metrics/functions when they are necessary to reproduce a P0 decision. |

## Prohibited shortcuts

- Do not import anonymous OWL restrictions as catch-all entities or relationships.
- Do not make a FIBO source class appear to be an actual portfolio, security, legal entity, or market price.
- Do not encode business meaning only in an ID, free-text note, or an unverified calculated field.
- Do not add a metric, function, or Skill merely to mirror a table join. The PRD must identify the decision and the implementation must show why declarative BKN relations and a documented query are insufficient.
- Do not use real client, issuer, price, transaction, or LEI data.
