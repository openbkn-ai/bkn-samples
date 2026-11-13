# 0.1.19: new kit status "Covered (Order Pending)"

Based on 0.1.18. Business data, objects, relations and actions are unchanged.

**Covered (Order Pending)**: kit schedule plans get a third kit status, "Covered (Order Pending)". When the only missing materials have no purchase request yet and arrive before the planned start if ordered now, the schedule Gantt's Kit_Check lets the plan be adopted, but the plan writer recorded it as Short. Such a plan is now recorded as "Covered (Order Pending)". Its kit date is the earliest kitted date, and the shortage note says purchase requests are needed before the planned start and lists the materials to order. Covered and Short keep their meaning. The installed scheduling history is regenerated the same way: two plans change from Short to "Covered (Order Pending)". The knowledge-network field description and the Skill are updated to match.

Existing installations keep their version; changing versions follows the standard uninstall/install flow, which removes sample-owned data and resources. No in-place migration is provided.
