# 0.1.4: calculation functions run as actions

Based on 0.1.3. The three calculations (inventory as of a date, order allocation and replenishment, and recall control assessment) are no longer mounted on the knowledge network; each is a tool action (`retail_gs1_en_us_inventory_asof`, `retail_gs1_en_us_fulfillment_plan`, `retail_gs1_en_us_recall_assessment`), following the OpenBKN 0.2.2 action model. Objects, relations, business data, calculation logic and the business scope of the Skills are unchanged.

Every input of an action is required: products, business date, knowledge cutoff, recall and the location, lot, order and trace scope, allocation or replenishment mode and replenishment horizon are the assumptions of each calculation, so the Agent passes them on every run and the execution record shows what the answer assumed. A scope the user did not limit is passed as an empty list or empty string; the function treats an empty string as not set.

The Agent reads the parameters with `get_action_info`, runs `execute_action` and reads the result with `get_action_execution`. Requires OpenBKN 0.2.2 or later with openbkn-ai/bkn-foundry#3125 (interaction context for function actions).

The experience card on stock that cannot be determined (Q-41) now gives root causes, matching what the inventory calculation reports: a sale recorded twice with different quantities, arrivals with no matching dispatch, and stock going negative. Its answer explains each reason in business terms.

Existing installations keep their version. To change versions, uninstall and install as usual; uninstalling removes the sample data and owned resources. No in-place migration is provided.
