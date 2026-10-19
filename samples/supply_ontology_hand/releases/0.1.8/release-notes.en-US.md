# 0.1.8

- Each native function is published as one readable Python source file containing only the calculation code it uses, instead of a base64 archive of every module packed into each function. Function names, parameters and results are unchanged.
- Functions read the knowledge network through the sandbox's preinstalled `bkn_osdk`, which uses the public BKN interface with the gateway and credentials supplied by the runtime; no address is written in the code. Reads also work on OpenBKN 0.2.0 deployments with Trace capture disabled.
- Fixes kitting net demand and backward planning with `warehouse_scope=all`: inventory reads no longer send an empty warehouse condition, which the query service rejected; like the calculation, they apply no warehouse filter.
- No longer publishes agent Skills. The backward-plan business rules move to `docs/backward-plan-business-rules.md`; the skills object type in the knowledge network is unaffected.
- Data, the knowledge network model and metrics are unchanged. Uninstall an existing installation before installing this version; in-place migration is not supported.
