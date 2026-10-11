# Third independent sample acceptance

2026-10-11. Order basics 0.1.1 passed fresh offline and official online installation through the homepage, on the same fixed official Studio/service baseline.

- The fixed service does not bundle order-basics. The accepted offline package/current record and its owned database/network/catalog were backed up and removed before the online run; all historical attempts were retained.
- After official catalog publication, the homepage refresh discovered the new release without updating the client or installer. The online package was downloaded from its official Release and all five stages succeeded.
- Actual object queries returned three products, four orders and eight units. A standard managed MCP relation query returned all four order/product pairs, with amount 750.
- No functions, metrics or Skills are declared by this minimal sample. The capabilities stage passed and Studio displayed zero of each; no creator Skill was called.
- Failure and success remain separate across versions. Supply-chain and World Cup histories are unchanged. A restart of the same service image preserved the online success and all attempts.
- With no remote catalog cache and GitHub unreachable, the earlier 0.1.0 candidate was imported from the homepage, its local notes displayed and installation succeeded after permitting Kubernetes API access. The data image was preloaded; tar.gz does not contain image layers. This proves the empty-cache offline path, not an air-gapped image download.

## Corrections and version history

The initial candidate lacked KN JSON branch, fixed in reviewed PR106. Local imported notes were fixed in reviewed PR105. First online publication of 0.1.0 was refused because its generated receipt omitted the required capabilities check. PR108 withdrew that version without rewriting immutable references and aligned publication validation with existing installer checks. Replacement 0.1.1 was freshly installed and fully recorded before publication in PR109. No installer check was weakened.

Exact package, image, attempts, data and relation results: [JSON evidence](phase6-third-sample-acceptance.json). Additional components are covered by [supply-chain acceptance](phase6-component-acceptance.md) and [model/MCP acceptance](phase6-agent-acceptance.md). In-place upgrades remain unsupported.
