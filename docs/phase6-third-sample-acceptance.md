# Third independent sample acceptance

2026-10-11. The exact candidate passed fresh offline installation through the homepage. Online installation after official catalog publication remains pending until this publication PR is merged.

- The fixed Studio/service baseline does not list order-basics as bundled. No sample-specific client or installer branch is needed.
- With no official catalog cache and external GitHub access unavailable, the homepage imported the package, displayed its local release notes and accepted installation. The fixed data image was preloaded; tar.gz does not contain image layers.
- After correcting the test proxy scope to permit Kubernetes API access, the homepage retried the same version and all five stages passed. Failures and success remain separate; supply-chain and World Cup histories are unchanged.
- Actual queries returned two data-backed objects, one relation, three products, four orders, eight units and joined amount 750.

Initial preflight exposed the missing KN JSON branch, fixed by reviewed PR106. The imported notes endpoint was fixed by reviewed PR105. Failed candidates were not added to the official catalog.

Exact artifacts and records: [JSON evidence](phase6-third-sample-acceptance.json). This sample declares no functions, metrics or Skills; see [supply-chain component acceptance](phase6-component-acceptance.md) for those components.
