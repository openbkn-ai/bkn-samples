# Executor compatibility for fixed releases

A published sample's platform range does not prove that the executor exposes the
commands used by its hooks. Supply-chain 0.1.4 remains published, while the default
SDK 0.2.1 executor lacks its legacy metrics commands. Installation can otherwise
create resources before failing.

`installer/executor_compatibility.json` is a reviewed constraint overlay keyed by
immutable release manifest SHA256. It changes neither the published archive nor
its platform range. The initial entry binds manifest
`147cfecf87311bcdd0cb09bb88490c630e20aac7dbab8fc0441958258b46d281` to package
`cb0d3f01568c490dca22fdd4ff6273dc83804f6726a3c5c8872e4eb670a14ad0` from the
[original release](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-supply-chain-v0.1.4).
The JSON records that immutable package identity and download source. Renaming a
sample preserves the check; another manifest is not assumed to need these commands.

The requirements follow the archive's automatic install and verify hooks:

| Original script | Command requirements |
| --- | --- |
| `tools/power_layer.py` | `bkn metric list/create/query`, `bkn object-type get/update/query` |
| `tools/import_kn.py` | `bkn get`, root `call` |
| `tools/setup_catalog.py`, `tools/bind_kn_resources.py` | `vega catalog list/resources/get/create/enable/test-connection/discover`, `resource find/list` |
| `tools/register_native_function_toolbox.py` | `toolbox list/publish`, `tool list/enable/disable`, root `call`, `bkn capability attach` |
| `tools/register_skills.py` | `skill list/register/update-package/set-status`, `bkn capability attach` |
| `platform/verify_platform.py` | `bkn capability list` plus the above list/query commands |

Existing-resource and lookup fallback branches are included because installation
can take those branches. Optional `import_kn.py --resolve-embedding` is not invoked
by `platform/install_supply.py`; its `model small get-default` command is not a
requirement. Native toolbox/tool creation uses root `call`, so no invented
`toolbox create` or `tool create` requirement is added.

The probe resolves `openbkn` using the same PATH supplied to hooks and executes
only command-group `--help` with temporary HOME/cwd and no token or platform URL.
Ten groups share one five-second budget; each subprocess receives the remaining
budget. Exact usage (including explicit CLI aliases) and required subcommand rows
must match. Exit zero with parent help is insufficient. Missing CLI, malformed help,
errors, or timeout fail closed; an unsuccessful probe does not prove a command is
absent. Results, including failures, are cached by command requirements for the
immutable runtime instance. Restarting/replacing the executor creates a new cache.

This is not an SDK-version allowlist. Actual offline fixtures show the original
published executor's SDK 0.2.0 command tree passes all ten groups. SDK 0.1.4 passes
metrics but lacks capability attachment; SDK 0.2.1 lacks legacy metrics. The
original README's SDK 0.1.4 statement alone is therefore insufficient. Version
strings do not establish protocol compatibility.

Catalog cards expose the safe specific reason through the existing `message`
field for uninstalled samples. Existing failed/installed cards retain their
original error and uninstall action, with separate `compatibilityMessage` metadata.
Direct install/retry returns 409 `runtime_upgrade_required`. Worker execution
rechecks before downloads/hooks/platform mutations. Receipt identities and uninstall
eligibility are unchanged. Unrelated generic platform failures retain the existing
bundled-card fallback.

Passing this offline probe does not prove server API availability, authentication,
SDK engine compatibility, or end-to-end acceptance. Existing platform/capability
checks still apply. No platform upper bound or license inference is introduced.
Unknown digests remain governed by their original requirements: this is an audited
correction, not static analysis of arbitrary hooks. The installer directory is copied
into the Studio image; executor source hashing covers its Python and JSON files.

A future catalog protocol may carry these capabilities explicitly. This overlay
also protects old cached catalogs and retry receipts without silently rewriting
immutable release metadata.
