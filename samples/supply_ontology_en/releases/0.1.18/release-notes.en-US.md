# 0.1.18: plan records match the Gantt's kit check

Based on 0.1.17. Business data, objects, relations and actions are unchanged.

**One kit result**: the kit result recorded when a kit schedule plan is created or adjusted now matches the schedule Gantt's Kit_Check exactly. Both use the same calculation: signed backlog first, then confirmed and scheduled plans in start order, sharing stock and on-time purchases with the network's other active plans; products already in production have drawn their materials and are skipped; the shortage note names the plan's own start. Before, a plan in production that passed the Gantt check could be recorded short after a move, with the business date as its start. The installed scheduling history is produced by the same calculation.

Existing installations keep their version; changing versions follows the standard uninstall/install flow, which removes sample-owned data and resources. No in-place migration is provided.
