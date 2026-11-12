# 0.2.10: calculation functions mounted on the network

Based on 0.2.9. The three calculations (settlement status, valuation and limit assessment as of a date) analyse the network without changing any object, so they are mounted on the knowledge network as functions again instead of running as tool actions, and the 0.2.9 tool actions are removed. The Agent calls them with Context Loader `execute_tool`, and platform verification now requires each enabled function to be mounted on the network. Objects, relations, business data, calculation logic and the business scope of the Skills are unchanged.

Requires OpenBKN 0.2.2 or later.

Existing installations keep their version. To change versions, uninstall and install as usual; uninstalling removes the sample data and owned resources. No in-place migration is provided.
