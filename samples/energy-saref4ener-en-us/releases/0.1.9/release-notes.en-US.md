# 0.1.9: calculation functions mounted on the network

Based on 0.1.8. The three calculations (eligible reduction, dispatch plan and settlement for events) analyse the network without changing any object, so they are mounted on the knowledge network as functions again instead of running as tool actions, and the 0.1.8 tool actions are removed. The Agent calls them with Context Loader `execute_tool`, and platform verification now requires each enabled function to be mounted on the network. Objects, relations, business data, calculation logic and the business scope of the Skills are unchanged.

Requires OpenBKN 0.2.2 or later.

Existing installations keep their version. To change versions, uninstall and install as usual; uninstalling removes the sample data and owned resources. No in-place migration is provided.
