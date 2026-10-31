# Financial Portfolio Operations (FIBO reference, English)

A fictional asset manager's post-trade controls, tracing instruments, legal entities and portfolios through trades, settlement, positions, prices, valuations, issuer concentration and unsettled-sale receivable limits. The sample includes 20 tables, an ontology, 3 native functions and 2 business Skills. Business requirements and rules are in the [PRD](docs/PRD.md).

## Install and explore

1. Sign in to OpenBKN and open **One-click onboarding** from the homepage.
2. Refresh the official catalog, select **Financial Portfolio Operations (EN)** and click **Install**; it requires **OpenBKN >=0.2.1 <0.3.0**.
3. Wait for installation and verification to complete, then open the knowledge network.
4. Try the experience cards on the Q&A, data query and graph pages, or connect an external agent through MCP to query objects, call published functions and use Skills.

If the official catalog is unreachable, download this sample's `package.tar.gz` from [Releases](https://github.com/openbkn-ai/bkn-samples/releases), choose **Import offline package** in one-click onboarding, then install it. See [offline installation](docs/offline-installation.md).

The data is synthetic and covers November 2026 to March 2027, with business date 2027-02-28: November to February are actual, March is the plan known that day. It is not real market data, official NAV or regulatory risk measurement, and nothing places orders or changes records.

## Capabilities

Anything Cypher can answer has no function; functions are kept only for recomputation Cypher cannot express. The sample uses no metrics, so the Community edition can use all of it.

- **Cypher queries**: master data, trades and settlement, month-end positions, valuations, issuer exposures and their contributions, counterparty receivables, limit assessments and limit versions. Month-end snapshots match recomputation from the original records and can be read directly.
- **Native functions**: `settlement_asof`, `valuation_asof` and `limit_assessment_asof` recompute settlement status, position valuation and limit decisions from the original trades, settlement events, prices and limits for a given date and what was known that day, for dates that are not month ends or for looking back at an earlier day.
- **Skills**: organized for the users, "Post-trade operations" (middle office, accounting) and "Risk and limits" (risk, portfolio manager), stating the business rules, when to use Cypher, when to call a function, and how to answer.

## Experience cards

The experience cards are taken from the test set and cover settlement, valuation, concentration, counterparty receivables, future limits and look-back, from simple to complex. The cards' data query and graph Cypher are checked online after installation with `tools/acceptance/experience_set.py`.

## Acceptance and maintenance

See the [business-scenario test set v1](bkn-eval/baselines/2026-10-30-business-scenarios-v1/README.md). Reference answers are computed by an independent script from the delivered data and are not shipped in the package. After installation, an agent that has not read the answers runs each question once; below 100%, record why each failed and fix the ontology descriptions, Skills or functions first, never the questions or answers. The original 100-question replay and data checks are in [bkn-eval](bkn-eval/README.md).

For the ontology and its FIBO alignment see the [modeling specification](docs/bkn-modeling-spec.md) and [FIBO mapping](docs/fibo-operational-mapping.md). The source is [EDM Council FIBO](https://github.com/edmcouncil/fibo) at pinned revision `2d73435a4419b66b7c9f44cb9763e35fe8ac7890`, MIT licensed; the original RDF is in [fibo-reference/](fibo-reference/README.md).

To install a new version, uninstall the existing sample first. Uninstallation removes sample data and user edits; deleting a cached offline package does not uninstall installed resources.
