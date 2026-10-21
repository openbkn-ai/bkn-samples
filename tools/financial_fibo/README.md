# Financial FIBO sample authoring

The sample entrypoints are `samples/financial-fibo-en-us/README.md` and `samples/financial-fibo-zh-cn/README.md`. Both are local offline candidates with model, data and evaluation deliveries.

The authoring tools require Python 3.9+ and standard libraries. `build.py` creates deterministic fictional records, native BKN files, source inventories and query-derived gold. `docs.py` renders the readable documentation and full answer tables. `assets/verify.py` independently reconstructs financial facts; `assets/run.py` replays frozen answers. Copies of these standalone tools are included in each sample. `test_financial_fibo.py` validates bilingual equivalence and injects wrong facts to prove that the verifier rejects them.

To reproduce source-derived files, use an official FIBO checkout fixed at `2d73435a4419b66b7c9f44cb9763e35fe8ac7890`:

```bash
python3 tools/financial_fibo/build.py --fibo-source /absolute/path/to/pinned-fibo
python3 tools/financial_fibo/docs.py
```

Regeneration intentionally rewrites the dataset locks and gold; it is an authoring operation to review, not validation. Routine validation must not call the generator:

```bash
python3 tools/financial_fibo/test_financial_fibo.py
openbkn bkn validate samples/financial-fibo-en-us/kn
openbkn bkn validate samples/financial-fibo-zh-cn/kn
python3 samples/financial-fibo-en-us/bkn-eval/run.py
python3 samples/financial-fibo-zh-cn/bkn-eval/run.py
```

Shared-database loading, native BKN resource binding and local 8081 installation have been implemented. Actual agent/MCP results are recorded separately in local acceptance reports; these candidates are not published.


Capability runtime lives in each sample tools/post_trade.py (identical core), managed_execution.py and register_capabilities.py; it uses the official SDK, not fixture files. Run `python3 tools/financial_fibo/test_capabilities.py` for independent snapshot reconciliation and adverse controls. `build_capability_questions.py` is authoring-only and produces implementation-derived public development references; never call it during evaluation. Independent heldout cases and gold are not shipped.

`test_known_fields.py` adds independently authored synthetic counterexamples for USD identity conversion and same-day cost ambiguity, including proved-zero exposures, negative controls and bilingual known-field/evidence preservation. Run it together with the snapshot suite; fixture files are test-only and are not installed.
