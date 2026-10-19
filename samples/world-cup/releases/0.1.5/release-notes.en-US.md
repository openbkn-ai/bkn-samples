# 0.1.5

- Adds three native functions mounted to the World Cup knowledge network: top scorers (competition ranking by non-own goals, ties kept), player career (editions, goals per tournament, awards) and tournament summary (matches, match goals, goals per match, own goals, shoot-out kicks).
- Each function is one readable source file that reads the network through the sandbox's preinstalled `bkn_osdk` (`run_cypher`, `query_object_instance`); the gateway and credentials come from the runtime, never from the code.
- Installation verification calls the top-scorers function and checks the WC-2022 top scorer, P-64077 with 8 goals.
- Data and the knowledge network model are unchanged. Uninstall an existing installation before installing this version; in-place migration is not supported.
