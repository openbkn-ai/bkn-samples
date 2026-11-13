# 0.1.8: display names (OpenBKN 0.2.2)

The Workshop scheduling wizard, the Gantt and Q&A show business names instead of field IDs. Data, rules and action behaviour are the same as in 0.1.7.

- **Property display names**: all 240 properties of the 40 objects have display names, in Chinese in the Chinese sample (计划开始日, 计划机台, 状态 …) and in English in the English sample (Planned Start Date, Planned Machine, Standard Duration (Days), Status, Machine ID, Machine Name …). Property IDs are unchanged.
- **Relation display names**: the 73 relations are named after the field that links them, e.g. "Manufacturing Operation → Production Order", "Manufacturing Operation → Predecessor Operation", "Manufacturing Operation → Planned Machine" (制造操作的生产工单 … in the Chinese sample). Relation IDs and Cypher patterns are unchanged.
- **Toolbox and function names**: rule functions and the functions behind the actions are in two toolboxes. The English sample has Manufacturing_Schedule_Rules (Work_Order_Kit, Machine_Capability, Operator_Qualification_And_Shift, Changeover, mounted on the network) and Manufacturing_Schedule_Adjustments (Adjust_Operation_Schedule, Adjust_Maintenance_Work_Order, used by the two actions "Adjust operation schedule" and "Adjust maintenance work order"); toolbox and function names allow only Chinese, letters, digits and underscores; the Chinese sample has 制造业排程规则 and 制造业排程调整 with Chinese function names. ID-style names such as MANUFACTURING_en_us_Schedule are gone.
- **A failed install can be uninstalled**: the install hook writes an empty ownership receipt before it creates the first resource; before, a failure ahead of the first toolbox left no receipt and the sample service refused to uninstall.
- Upgrading from 0.1.7 means uninstalling 0.1.7 first (which removes its toolbox), then installing. The 50 existing bkn-eval answers are unchanged.

The sample's own Workshop "machine scheduling" app is not part of this version.
