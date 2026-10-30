# Sample Tools

The standard hooks run these tools to load the 12-table fixture, import the knowledge network, bind its independent catalog, and publish the native functions and Skills.

Users install through one-click onboarding or offline package import; see the [installation guide](../docs/import-guide.en-US.md). These scripts are internal installation helpers.

| Purpose | Script |
| --- | --- |
| Data loading | `load_sample_data.py` (called by `db/load_supply.py`) |
| Knowledge network import and binding | `import_kn.py`, `setup_catalog.py`, `bind_kn_resources.py` |
| Function and Skill publication | `register_native_function_toolbox.py`, `register_skills.py` |
| Platform acceptance | `smoke_test.py` |

`fn/planning.py` implements the two native calculation functions (buildable quantity and available to promise; demand coverage and shortages). `managed_execution.py` reads the facts each function needs at run time through `sandbox_sdk.bkn`, and the registration script bundles and publishes them. `config.example.yaml` is a developer reference; standard hooks generate the runtime configuration. `verify_sample.py` checks local delivery contracts.

Run offline checks from this sample directory:

```sh
PYTHONPATH=tools python -m pytest tools/tests -q
```

Offline checks do not replace a real installation and MCP business acceptance; see the [v4 business-scenario test set](../bkn-eval/baselines/2026-10-30-business-scenarios-v4/README.md).
