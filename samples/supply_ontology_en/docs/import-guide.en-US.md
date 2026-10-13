# Import and Acceptance

1. Prepare OpenBKN authentication and confirm the target environment. Use the standard sample offline package for one-click onboarding.
2. Install `supply-chain-en` with database `supply_demo_en` and knowledge network `supply_ontology_en`. Its standard hooks initialize and verify 12 tables, then import and bind the sample resources.
3. Confirm dataset hashes against `dataset.lock`, preserving leading-zero forecast IDs and all three future forecasts. Configure the independent catalog if importing manually.
4. Verify object types, relations, metrics and object logic-property bindings. English metrics have the `Supply EN:` prefix. Discover actual platform IDs at runtime.
5. Register the **Native Function Toolbox** `Supply_EN_Functions` and the five `supply-en-` Skills. `tools/fn/` holds sample calculations; callers do not build or pass `resolved_context`. Runtime functions read their bound BKN objects.

## Step 6: Capabilities and MCP Acceptance

Discover functions and Skills through actual MCP metadata. Read the published Skills and invoke the named functions with their declared parameters. Check resolved warehouse scopes, alternate policies, finished/component-first allocation, shared stock and leading-zero forecast lookup. Use the standard lifecycle for a clean candidate reinstall; do not upgrade in place or remove unrelated samples.

## Step 7: Core 50-Question Evaluation

Use only `bkn-eval/datasets/sample-question-set-v1.yaml` for the core questions. A blind independent agent answers through MCP without CSVs, answers or implementation source. A separate judge compares required business outputs against the independent CSV gold. Require exact agreement for all 50 questions.

Run the four complete-calendar-month questions separately. Verify the published Monthly Sales Skill, half-open Asia/Shanghai boundaries, May 31 inclusion, identical filters and agent arithmetic. Do not substitute a server-side `sameperiod` diagnostic for this business path.

Keep exact package/image digests, installation receipts, discovered capability IDs, calls, answers and judgments in a local workspace outside the committed sample. Execution success or a previous package's score is insufficient evidence.
