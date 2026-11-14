# 0.1.22: business wording in the app; exports reuse as they are

Based on 0.1.21. Business data, objects, relations, functions and actions are unchanged.

**The Kit Scheduling app**:
- On the demand view, plan bars show the kit status only, without the line code. Each row's status names the line, and the line code is in the popover.
- Tray cards show the forecast quantity.
- "Planned resource" is now "Planned line". Rule names read Kit check and Line can build in business words; the functions they call are unchanged.

**Exports reuse as they are**: the installer accepts an app file exactly as the app workshop exports it. Its app ID from the source environment is not used. Its toolbox and tool IDs are looked up again by toolbox and function name in this installation and replaced. The sample docs add how to reuse an app in a customer environment: export it, prepare the objects and functions it needs, import it, and fit it to the customer's data.

Existing installations keep their version; changing versions follows the standard uninstall/install flow, which removes sample-owned data and resources. No in-place migration is provided.
