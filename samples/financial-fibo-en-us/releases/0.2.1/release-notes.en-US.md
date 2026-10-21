# 0.2.1 — Local post-trade controls candidate

Requires OpenBKN >=0.2.1 <0.3.0. Unpublished; PR183 remains a draft.

- Retains2 recorded metrics,3 atomic read-only functions and1 investigation Skill with explicit ratio/USD semantics.
- Separates Chinese branch labels from settlement states and adds due date, source failure reason and quantity units.
- Compares recorded position/valuation caches after reconstruction, with field differences and source evidence; caches never drive calculations.
- Loads capability-specific sources using SDK IN and bounded complete pagination for broad investigations.
- Adds public response-field contracts; original100-question gold and78,356 fictional source records stay unchanged.

Actual model conversations, independent holdout, live perturbations, failures and three-round stability are reported in separate acceptance artifacts. Deterministic replay and local tests are not model business accuracy.
