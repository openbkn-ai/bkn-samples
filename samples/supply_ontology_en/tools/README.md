# Sample Tools

The standard hooks run these tools to load the 12-table fixture, import the knowledge network, bind its independent catalog, create/bind metrics, and publish native functions and Skills.

Use `config.example.yaml` for manual development and `sample.yaml` for the standard installer. Runtime functions read BKN through `sandbox_sdk.bkn`; CSVs are limited to initialization and offline checks. `function_catalog.py` defines the named operations; `native_function_bundle.py` creates their runtime bundle. `verify_sample.py` checks local delivery contracts.

Run offline checks from this sample directory:

```sh
PYTHONPATH=tools python -m pytest tools/tests -q
```

Actual acceptance additionally requires a standard package installation and independent MCP evaluation. Do not treat offline checks as proof of the agent path.
