# 0.1.8

- Each native function is published as one readable Python source file containing only the calculation code it uses, instead of a base64 archive of every module packed into each function. Function names, parameters and results are unchanged.
- Functions read the knowledge network through the sandbox's preinstalled `bkn_osdk`, which uses the public BKN interface with the gateway and credentials supplied by the runtime; no address is written in the code. Reads also work on OpenBKN 0.2.0 deployments with Trace capture disabled.
- Fixes kitting net demand and backward planning with `warehouse_scope=all`: inventory reads no longer send an empty warehouse condition, which the query service rejected; like the calculation, they apply no warehouse filter.
- Data, the knowledge network model, metrics and Skills are unchanged. Uninstall an existing installation before installing this version; in-place migration is not supported.

The package uses the product-provisioned shared sample database and requires the OpenBKN 0.2.0 patch providing that capability.
