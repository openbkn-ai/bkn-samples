# Agent Operation Guide: API, CLI, and Scripts

## Goal

The Agent does not depend on the web UI. It uses OpenBKN APIs, the `openbkn` CLI, and sample scripts to import, bind, verify capabilities, and answer a fulfillment commitment question.

## Step 1: Human database-table import (Agent prerequisite)

This step must be performed by the deployment/POC operator because it requires database connection details and a password. From the sample root, run:

```bash
python3 tools/load_sample_data.py --interactive --create-database --table-prefix hand_
```

Enter the PostgreSQL host, port, database, username, and password. The script tests the connection and writes only after you type `yes`; destination tables use the `hand_` prefix. Agent automation starts after Catalog Discover.

## Operation entry point

```text
Agent → OpenBKN API / openbkn CLI → KN, Resources, Skills, Functions, Actions → test set and report
```

Recommended entry sequence:

```bash
openbkn auth status
python3 tools/import_kn.py --json kn/supply_ontology_hand_en.json --dry-run
python3 tools/setup_catalog.py --interactive --table-prefix hand_ --write-config
python3 tools/import_kn.py --json kn/supply_ontology_hand_en.json --resolve-embedding
python3 tools/bind_kn_resources.py --config tools/config.poc.yaml --kn-id supply_ontology_hand_en --table-prefix hand_
python3 tools/register_skills.py --dry-run
python3 tools/setup_skill_dataset.py --interactive --apply --kn-id supply_ontology_hand_en
python3 tools/setup_catalog.py --config tools/config.yaml --write-config
python3 tools/bind_skill_dataset.py --kn-id supply_ontology_hand_en --catalog-id <catalog-id> --apply
python3 tools/bootstrap_action_layer.py \
  --config tools/config.poc.yaml \
  --interactive --apply
```

### Platform implementation constraints

- Toolbox names may contain only Chinese characters, letters, digits, and underscores. Do not use hyphens, spaces, or other punctuation; use `SupplyChainFunctionToolsP0`, not `SupplyChainFunctionTools-P0`.
- Before creating a Toolbox, check `openbkn toolbox list` by name. If the POC request times out, run `openbkn auth status` and list Toolboxes before retrying, so a successful create is not duplicated.
- Keep the function service running and configure it through `FUNCTION_SERVICE_URL`. The URL must be resolvable and reachable from the OpenBKN/POC network; local browser reachability does not prove platform-container reachability.
- Tools uploaded from OpenAPI may default to `disabled`; capture the returned `tool_id` values, run `openbkn tool enable --toolbox <box-id> <tool-id...>`, and verify that every tool is `enabled`.
- Agent mode uses `bootstrap_action_layer.py` to apply idempotent DDL, verify the three tables, and bind object types in one flow. The password is used only during the prompt and is not written to `config.poc.yaml`.
- The Skill Registry is also a database table: run `setup_skill_dataset.py` to create it and upsert published Skills from the current environment, Discover the Catalog again, then bind object class ID `skills` with `bind_skill_dataset.py`. Skill API registration alone is not sufficient for `find_skills`.
- Use the individual `--dry-run` commands to inspect plans; after apply, verify both the database tables and `openbkn bkn object-type get` output.

Use dry-run for every platform write first. The Agent must rely on returned capabilities and evidence rather than guessing object types, fields, Skills, or Actions.

## Recommended user question

Can product `U00-000080` be delivered by `2026-10-31` in a quantity of `3000`? The forecast number is `0000023181-FUTURE`; do not use substitute materials. Explain inventory, producible quantity, material shortages, and the evidence for the conclusion.

## Verification sequence

1. Confirm that the knowledge network and data sources are ready.
2. Find the fulfillment analysis Skill.
3. Retrieve forecast, product, inventory, BOM, production, and purchasing evidence.
4. Call the function that calculates the deliverable quantity.
5. Return the conclusion, evidence, and risks.
6. Show a dry-run and impact scope before any Action and wait for confirmation.

## Executing orchestration Skills

S1/S2/S3 are orchestration Skills. The Agent reads the contract with `find_skills` / `get_skill_content`, then performs the managed data retrieval and function call. Do not invoke S1 as an `execute_skill` shell command without business parameters.

No additional context store is required: pass the existing `conversation_id` and `interaction_id` unchanged in `bkn_context`, assemble the existing snapshots and `bkn_receipt` values into `resolved_context`, and pass that object directly to `backward_plan`. The function calculates only; it does not query a database. The Agent renders the report according to the Skill contract.

The online call relationship is:

```text
optional Context Loader(bkn_context)
→ resolved_context(rows + receipts)
→ OpenBKN Toolbox REST Proxy(backward_plan, request body)
→ Agent report
```

The POC function Toolbox is callable; the Context Loader MCP catalog and the Toolbox catalog are separate. The Agent calls the tool through the OpenBKN Execution Factory REST Proxy and does not need to know the Toolbox's backend `FUNCTION_SERVICE_URL`. The administrator configures that backend only when creating/updating the OpenAPI Toolbox.

Production call endpoint:

```http
POST https://<openbkn-host>/api/agent-operator-integration/v1/tool-box/<box_id>/proxy/<tool_id>
Authorization: Bearer <token-or-appkey>
x-business-domain: bd_public
Content-Type: application/json
```

Put the function request in the envelope's `body`; use the returned `status_code` as the upstream function status. Do not use CSV, offline CLI, or an untraced direct call as a substitute for online success.

When a function only needs computation and no additional evidence retrieval, the Agent may skip Context Loader and call the REST Proxy directly. When supply-chain facts are required, query through the managed Context Loader first and put the resulting `resolved_context` into the function request.
