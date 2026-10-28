# Sample experience sets

Once a sample is installed, people need questions that show what it can do. An experience set takes questions from the sample's evaluation question and answer sets and adds a reference answer and the pages each question suits. Studio offers the cases one at a time on the Q&A, data query and graph explorer pages: clicking a case puts its question into the page's own input, and when the result is in, the reader compares it with the reference answer and marks it right or wrong.

- Schema: [`installer/schemas/experience-set.schema.json`](../installer/schemas/experience-set.schema.json)
- Validation: [`installer/experience_set.py`](../installer/experience_set.py)
- Live check: [`tools/acceptance/experience_set.py`](../tools/acceptance/experience_set.py)
- First sets: [supply chain (Chinese)](../samples/supply_ontology_hand/experience/experience-set.yaml), [supply chain (English)](../samples/supply_ontology_en/experience/experience-set.yaml)

## Location and declaration

A set lives at `experience/experience-set.yaml` in the sample directory and is declared in `sample.yaml`:

```yaml
spec:
  studio:
    experienceSet: experience/experience-set.yaml
```

Packages leave `bkn-eval/` out, so a set carries its own questions, answers and expected values and needs nothing from the evaluation folder after installation. `metadata.source` names the answer set it was taken from, and a repository test keeps the two in step. The set's language must equal the sample's `metadata.language`.

## Format

```yaml
apiVersion: samples.openbkn.ai/v1alpha1
kind: ExperienceSet
metadata:
  language: en-US
  source:
    answerSet: bkn-eval/datasets/sample-answer-set-v1.yaml
    setId: supply-en-question-set-v1
spec:
  businessDate: '2026-08-25'        # the frozen date the answers hold for; shown with every case
  cases:                            # in the order Studio offers them
  - id: R-05                        # the source answer-set id
    title: Products that use a material   # card title, at most 40 characters
    explanation: Walks the BOM relations back from a material to products.
    question: Which products use material 321-000569?   # verbatim from the source
    answer: Material 321-000569 is used by three products: P61-000328, P61-000331 and P61-000351.
    expected: {product_codes: [P61-000328, P61-000331, P61-000351]}   # verbatim from the source
    surfaces: [agent, query, graph]
    cypher:
      query: |-                     # columns are named after the expected fields
        MATCH (p:...)-[...]->(m:... {material_code: '321-000569'})
        RETURN DISTINCT p.material_number AS product_codes
      graph: |-                     # returns the nodes and relations to draw
        MATCH (p:...)-[r1:...]->(b:...)-[r2:...]->(m:...) RETURN p, r1, b, r2, m
```

## Rules

1. **Take, do not rewrite.** `question` and `expected` equal the source answer set exactly, and `id` exists there. When the source gold changes, the repository test reports the set as out of date.
2. **Answers are for people.** `answer` is one complete business conclusion that names every number and code in `expected`; yes/no flags need not appear word for word, but the conclusion must make them clear.
3. **Choose pages per question.** Every case can be tried in Q&A, so `surfaces` always includes `agent`.
   - `query` (data query): the answer follows from property filters, a fixed relation path and count/sum, without business-function rules. `cypher.query` is required, and its columns are named after the `expected` fields.
   - `graph` (graph explorer): the answer is a small set of entities reached through relations from a named node, readable at a glance on the canvas. `cypher.graph` is required and returns at most 50 paths.
   - Questions that need a function or skill (sellable quantity, coverage, delivery dates, competing demands) are `agent` only.
4. **Reference Cypher stays out of the input.** Studio puts only `question` into a page's input; the reference Cypher is shown as a "reference query" after the result.
5. **Answers stay out of the agent's context.** `answer` and `expected` are shown to the reader only, never added to the question or passed to an agent, keeping the gold set hidden from the evaluated side.
6. **Curated, not complete.** A set holds representative questions that show the capability plainly, 15–25 as a guide, from simple facts to relations to business decisions.

## Reading it after installation

When an installation or retry succeeds, the sample service records that version's experience set with the installation; the package itself is not kept. Studio reads it for the current knowledge network:

```http
GET /api/studio/samples/experience-sets/{knowledgeNetworkId}
```

Any signed-in user may read it. It returns `{sample, version, knowledgeNetwork, experienceSet}` only when a sample installed successfully and its record names this network as the one it created (`resources.knowledgeNetworkId`). Anything else, including a hand-made network with the same id, a failed installation, or an installed version without a set, returns 404 `experience_set_unavailable`, and Studio shows no experience mode. A set is available only after installing a version that contains it; an older installed version must be reinstalled.

A package that declares an experience set requires the `sample.experience-set` capability in `requires.capabilities`. Sample services that do not record experience sets reject such a version before downloading it and keep offering the previous one. An operator who sets an explicit `platform.capabilities` list must add this name to install these versions.

## Comparing expected values with a query result

The live check and Studio compare a `cypher.query` result this way:

| `expected` field | Comparison |
| --- | --- |
| Number or text | One result row; the column of that name is equal. Numbers compare as decimals, so `534.000000` equals `534`. |
| List of values | The column of that name across all rows, compared as a set. |
| List of records | All result rows, compared as records whose fields are the columns. |

## Validation

- Offline: `python -m unittest installer.tests.test_experience_set` checks the schema, that answers name every expected value, that surfaces and Cypher match, and that the set agrees with its source. The sample contract (`validate_document`) also checks a declared set, so package import checks it too.
- Live: on a platform with the sample installed, confirm every reference query reproduces its expected values and every graph query is small enough for the canvas. The token is read from the environment and never printed.

```bash
OPENBKN_TOKEN=<token> python3 tools/acceptance/experience_set.py samples/supply_ontology_en --base-url http://localhost:8081
```

## First supply chain sets

Both languages use the same 23 questions. The Chinese set takes `business-rules-v3`, the gold set that is current and matches the published data; the v1 answer set in `datasets/` belongs to the 2026-08-13 historical snapshot and differs from the published data on M-07, M-08 and M-12. The English set takes its `datasets/sample-answer-set-v1.yaml`.

| Page | Questions |
| --- | --- |
| Q&A (23) | All; F-04, F-15, F-10, S-01, S-04, S-02, S-10, S-07 and S-08 are Q&A only. |
| Data query (14) | M-04, M-06, M-10, M-12, M-15, F-07, F-01, R-02, R-05, R-07, R-08, F-02, F-14, R-09 |
| Graph explorer (5) | F-01, R-02, R-05, R-08, R-09 |

R-07 (30 products, 228 paths) and R-03/R-04 (complete multi-level BOMs) are too large for the graph explorer. Checked on a local 8081 platform on 2026-10-27: all 14 reference queries in both languages reproduce their expected values, and the 5 graph queries return 4–19 paths.
