# Sample Tools

The standard hooks run these tools to load the 12-table fixture, import the knowledge network, bind its independent catalog, create/bind metrics, and publish native functions and Skills.

Users install through one-click onboarding or offline package import; see the [installation guide](../docs/import-guide.en-US.md). These scripts are internal installation helpers. `config.example.yaml` is a developer reference; standard hooks generate the runtime configuration from installer input. Runtime functions read BKN through `sandbox_sdk.bkn`; CSVs are limited to initialization and offline checks. `function_catalog.py` defines the named operations; `native_function_bundle.py` creates their runtime bundle. `verify_sample.py` checks local delivery contracts.

Run offline checks from this sample directory:

```sh
PYTHONPATH=tools python -m pytest tools/tests -q
```

Actual acceptance additionally requires a standard package installation and independent MCP evaluation. Do not treat offline checks as proof of the agent path.

### Structured conclusion evidence (source candidate)

The native `bom_shared_list` Function optionally emits `trace_evidence` for the common material set and count under its product, depth and substitute policy. The sample owns all business validation and its existing 5,000-row protection; `fn/trace_evidence.py` makes no stock, kitting or order-acceptance assertion. Invalid/incomplete results omit the declaration; a zero intersection is valid.

Capture requires Foundry's `function_result_evidence/v1` support and explicit operator approval of the actual tool version and code hash. Older platforms can still use the existing business result. This source change does not publish/re-register Functions, alter existing artifacts or enable Trace. Publish a fresh candidate and recheck its approved hash separately.
