# 0.1.22: faster kit check, descriptions for business users

Based on 0.1.21. Business data, objects, relations, calculation rules and actions are unchanged.

**Faster kit check**: opening a plan's shortage detail in the schedule Gantt took more than 20 seconds and sometimes timed out; it now takes about 3 seconds, and batch checks are faster too. The functions read only the fields the calculations use, in larger pages; the BOM is read in one query without substitute lines (the kit check does not use substitutes); stock, purchases, sales orders and materials are read in parallel. The buildable-quantity and demand-coverage calculations read the same way. Results are the same as in 0.1.21.

**Descriptions for business users**: the Workshop wizard shows the descriptions of the kit check and line-can-build rules and of the create, adjust and cancel kit schedule plan actions; they now state the business meaning only, and how to call them stays in the parameter descriptions.

Existing installations keep their version; changing versions follows the standard uninstall/install flow, which removes sample-owned data and resources. No in-place migration is provided.
