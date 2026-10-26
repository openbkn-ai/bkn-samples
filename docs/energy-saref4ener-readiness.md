# Manufacturing and Energy integration for OpenBKN 0.2.1

All 13 sample identities are now in the source tree and in
[one candidate plan](../tools/publication/candidates-0.2.1.json). The four additions
to the earlier candidate coverage are Manufacturing EN/ZH **0.1.3** and Energy
SAREF4ENER EN/ZH **0.1.5**. They use content-only shared-MariaDB packages and retain
native BKN formats and declared capabilities. Stable catalog admission still
requires the target OpenBKN acceptance; candidate construction does not create a
successful platform verification receipt.

## Manufacturing

Each language retains 40 operational tables, 2,700 records, 71 relations, the IOF
reference layer and the 100-question bank. Database columns now match the model's
decimal, integer and day-level date types. `forecast_period` is explicitly a
YYYY-MM string; converting a month into an invented day is not its business meaning.
The two unmodeled raw reference-ID columns are retained as strings in the complete
loading contract. Installation checks network ownership before import and verifies
resource bindings and live-object queries without overwriting unrelated networks.

## Energy source recovery

The previous temporary source area had lost data/model/reference/evaluation files.
The immutable local 0.1.3 archives restored delivered source and data; every retained
sparse-source file matched the same archive bytes. The old archive hashes and
recovery decisions are preserved in
[the recovery record](acceptance/samples-0.2.1/energy-recovery.json).

SAREF4ENER 2.1.1 and SAREF Core 4.1.1 Turtle files were fetched from their official
fixed-version URLs and matched the retained historical SHA-256 freeze. Actual
upstream BSD-3-Clause license files are pinned to official repository commits.
The source/reference inventories, locks and notices are included in each new
archive. They are semantic references, not OWL equivalence or ETSI certification.

Each language retains 15 tables, 14,787 synthetic records, 15 object types,
15 relations, 3 functions, 2 immutable version-1 object-instance snapshot metrics
and 1 investigation Skill. Its units are kW, kWh and CNY as declared by the business
contract. Recorded eligible power and delivered ratio remain dated snapshots,
not live recomputation or cross-date aggregates.

The original independent-oracle file was not retained. Question contracts and
structured reference projections were recovered from historical terminal records,
with per-record SHA-256 provenance and explicitly identified targeted revisions.
Local replay against these historical projections is regression, not a new Agent
accuracy score. Independent hand-built boundary tests and managed adapter checks
are retained separately. Original session/auth data and raw execution logs are
not copied into source or packages. Evaluation answers remain source-only.

## Complete delivery and remaining acceptance

The V1 audit now covers **8 metric-bearing samples / 34 definitions**. The shared
consumer, input schemas and independent CSV fixture expectations cover Energy too.
Manufacturing does not gain artificial metrics/functions/Skills.

The candidate-set builder rejects missing or duplicate sample identities, requires
clean committed source, verifies package digests and offline imports for declared
architectures, and checks that 0.2.0 rejects 0.2.1 packages. Those architecture checks
validate metadata, not native execution. Actual database hooks are tested locally
on an isolated temporary MariaDB separately from source-only checks.

Real fixed OpenBKN 0.2.1 install/retry/uninstall/replacement, CLI/API/MCP, function,
Skill and query-engine acceptance remains pending by the user's requested scope.
Historical package bytes, prior candidate releases and the 0.2.0 root catalog are
not overwritten. See [local evidence](acceptance/samples-0.2.1/README.md).
