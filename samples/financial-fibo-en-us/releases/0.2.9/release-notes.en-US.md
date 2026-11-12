# 0.2.9: calculation functions run as actions

Based on 0.2.8. The three calculations (settlement status, valuation and limit assessment as of a date) are no longer mounted on the knowledge network; each is a tool action (`financial_fibo_en_us_settlement_asof`, `financial_fibo_en_us_valuation_asof`, `financial_fibo_en_us_limit_assessment_asof`), following the OpenBKN 0.2.2 action model. Objects, relations, business data, calculation logic and the business scope of the Skills are unchanged.

Every input of an action is required: portfolios, business date, knowledge cutoff and actual or planned view are the assumptions of each calculation, so the Agent passes them on every run and the execution record shows what the answer assumed.

The Agent reads the parameters with `get_action_info`, runs `execute_action` and reads the result with `get_action_execution`. Requires OpenBKN 0.2.2 or later with openbkn-ai/bkn-foundry#3125 (interaction context for function actions).

Existing installations keep their version. To change versions, uninstall and install as usual; uninstalling removes the sample data and owned resources. No in-place migration is provided.
