# 0.1.4

- Removes the `vega_sql_execute` OpenAPI tool. It called Vega's internal interface with caller-supplied identity headers, which OpenBKN 0.2.0 rejects (403). Queries use the standard MCP tools `query_object_instance` and `run_cypher`, under the caller's own identity and object permissions.
- The sample no longer publishes functions; installation verification checks that every object type, relation type and concept group was imported.
- Data and the knowledge network model are unchanged. Uninstall an existing installation before installing this version; uninstallation also removes the `wc_vega_query` toolbox created by earlier versions.

The package uses the product-provisioned shared sample database and requires the OpenBKN 0.2.0 patch providing that capability.
