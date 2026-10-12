# Supply Chain EN

An independent English sample for OpenBKN. Explore orders, forecasts, BOMs, stock and procurement using concise fictional English names. This sample has its own database, knowledge network, metrics, functions and Skills.

Import its standard offline package through one-click onboarding. For manual development, follow [the import guide](docs/import-guide.en-US.md). Finish Step 7 with the core 50-question BKN-Eval; the four calendar-month checks are separate.

- Sample: `supply-chain-en`
- Knowledge network: `supply_ontology_en`
- Database: `supply_demo_en`
- Function toolbox: `Supply_EN_Functions`
- Business date: `2026-08-25`
- Candidate version: `0.1.0`

The fixture contains fictional people and companies, engineering specifications and stable business identifiers. Use the included forecast scenarios to explore stock coverage, shortages and shared demand allocation.

See [BKN-Eval](bkn-eval/README.md), [FAQ](docs/faq.md) and [release notes](releases/0.1.0/release-notes.en-US.md). Evaluation material and tests are excluded from the installable package. Candidate scores apply only to the exact tested package.

When `supply-ontology-en-v0.1.0` is published, obtain that frozen release with:

```sh
git fetch origin --tags --force
git clone --branch supply-ontology-en-v0.1.0 https://github.com/openbkn-ai/bkn-samples.git
```

The tag above is a planned release identifier, not a claim that this candidate has been published.
