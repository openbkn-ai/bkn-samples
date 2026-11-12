# 0.1.20: calculation functions become actions

Based on 0.1.19. The two calculations, 产品可做数量与可承诺量 and 需求齐套与缺料, are no longer mounted on the network; they are two tool actions (`supply_ontology_hand_build_capacity`, `supply_ontology_hand_demand_coverage`) in the OpenBKN 0.2.2 action model. Objects, relations, business data, the calculations themselves and the Skills' business scope are unchanged.

Substitutes, warehouse scope, need-by date, overdue purchases, reserving signed backlog and using finished goods are action inputs: they are business assumptions, passed on every run, so each execution record shows what the answer assumed. When the user does not say, the Agent passes the default documented in the Skills; an empty string means no need-by date. The business date stays fixed to the sample date and is not an input.

The Agent uses `get_action_info` for the parameters, `execute_action` to run, and `get_action_execution` for the result. Requires a platform with openbkn-ai/bkn-foundry#3125 (managed context for Function actions).

Existing installations keep their version; changing versions follows the standard uninstall/install flow, which removes sample-owned data and resources. No in-place migration is provided.
