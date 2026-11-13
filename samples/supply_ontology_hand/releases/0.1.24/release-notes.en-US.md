# 0.1.24: new kit status "齐套（待下单）"

Based on 0.1.23. Business data, objects, relations and actions are unchanged.

**Covered (Order Pending)**: kit schedule plans get a third kit status, "齐套（待下单）". When the only missing materials have no purchase request yet and arrive before the planned start if ordered now, the schedule Gantt's Kit_Check lets the plan be adopted, but the plan writer recorded it as Short. Such a plan is now recorded as "齐套（待下单）". Its kit date is the earliest kitted date, and the shortage note says purchase requests are needed before the planned start and lists the materials to order. Covered and Short keep their meaning. The installed scheduling history is regenerated the same way: two plans change from Short to "齐套（待下单）". The knowledge-network field description and the Skill are updated to match.

Existing installations keep their version; changing versions follows the standard uninstall/install flow, which removes sample-owned data and resources. No in-place migration is provided.
