# 0.1.5: calculation functions mounted on the network

Based on 0.1.4. The three calculations (inventory as of a date, order allocation and replenishment, and recall control assessment) analyse the network without changing any object, so they are mounted on the knowledge network as functions again instead of running as tool actions, and the 0.1.4 tool actions are removed. The Agent calls them with Context Loader `execute_tool`, and platform verification now requires each enabled function to be mounted on the network. Objects, relations, business data, calculation logic and the business scope of the Skills are unchanged. It keeps the 0.1.4 fix to the experience card on stock that cannot be determined (Q-41), which now gives root causes.

Requires OpenBKN 0.2.2 or later.

Existing installations keep their version. To change versions, uninstall and install as usual; uninstalling removes the sample data and owned resources. No in-place migration is provided.
