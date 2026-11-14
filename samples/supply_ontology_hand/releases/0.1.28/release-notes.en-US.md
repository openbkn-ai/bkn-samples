# 0.1.28: demand bars show the line name

Based on 0.1.27. Business data, objects, relations and actions are unchanged.

**The 齐套排产 app**: on the demand view, a scheduled demand's bar shows its kit status and the name of the line its plan is on, not only the kit status. The name comes from the plan's line, without changing the plan object. The popover lists both the line name and the line code.

**Faster rule functions**: when Workshop calls the kit check and the line check through the toolbox proxy, outside a conversation, they read objects through the ontology query API directly and no longer touch the sandbox's built-in BKN reader. The calls no longer leave empty directories in the sandbox's shared workspace, so they return faster. Inside a conversation they read as before. The results are unchanged.

Existing installations keep their version; changing versions follows the standard uninstall/install flow, which removes sample-owned data and resources. No in-place migration is provided.
