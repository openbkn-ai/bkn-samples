# 0.1.21: kit check batch and detail agree; clearer app

Based on 0.1.20. Business data, objects, relations and actions are unchanged.

**One kit check**: for the same demand, the shortage count in a batch check now equals what its detail shows. Both start from the network's active plans with the current scenario's changes: moved and cancelled plans, and plans the scenario makes for demands. A demand not yet scheduled is checked as the plan it would make at its suggested start, added on its own on top of those plans, and no longer takes stock from other unscheduled demands. Before, in the demand view, unscheduled demands shared stock with each other in the batch and showed more shortages than their detail.

**Line_Can_Build**: a task not yet on a line answers "not applicable" instead of failing.

**The Kit Scheduling app**:
- Plan bars on the line view show the product name and forecast number. The popover lists the plan scope (whole bill or one product), kit status, kit date, key material, shortage note, planner and source scenario.
- The Gantt takes the full width, with scenario changes below it.
- On the demand view, a scheduled demand's bar shows its plan's kit status and line.

Existing installations keep their version; changing versions follows the standard uninstall/install flow, which removes sample-owned data and resources. No in-place migration is provided.
