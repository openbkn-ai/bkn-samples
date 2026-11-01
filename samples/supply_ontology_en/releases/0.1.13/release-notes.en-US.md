# 0.1.13: remove the unbound Skills object type

The 0.1.12 candidate failed fresh-package acceptance: its `skills` / `Skills` object type had no published data source and returned HTTP 503. Remove only this object type, leaving 11 business objects and the same 14 relations. Data, functions, Skill files and their registration are unchanged. This applies the Chinese #217 correction to the English sample.

The optional installation diagnostics from 0.1.12 remain included. Keep that failed draft and its digest as evidence; do not publish it or overwrite its package. This new candidate requires its own installation, retry and uninstall/reinstall acceptance.

Existing installations require the standard uninstall/install flow after preserving required data and edits. Uninstall removes sample-owned data and resources; no in-place migration is provided.
