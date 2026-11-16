# 0.1.30: Applying a schedule scenario writes the plans back

Based on 0.1.29. Business data, objects, relations, actions and the 齐套排产 app are unchanged.

**Actions such as "调整齐套排产计划" complete**: when Workshop applies a scenario, or an action runs in a conversation, the functions read the BOM, stock and purchase requests page by page with the cursor the query service returns instead of an offset. These hold more than 10,000 records; the second page used to be refused, so the action failed and no plan was written. All records are now read. 0.1.29 fixed the kit checks on the page; this version fixes the same issue for actions and conversations. The calculations are unchanged.

Existing installations keep their version; changing versions follows the standard uninstall/install flow, which removes sample-owned data and resources. No in-place migration is provided.
