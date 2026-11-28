# 0.1.12: objects show by name (OpenBKN 0.2.2)

Data, rule functions, actions and the Machine Scheduling app are the same as in 0.1.11.

- **Objects show by name**: twelve object types whose names are unique now take the name as their display key, in place of the ID: bills of materials, customers, equipment capabilities, inventory locations, maintenance plans, manufacturing sites, operators, production machines, products, routings, suppliers and work centres. A machine now reads "5-axis Mill 3" rather than MACH-MILL-03 in titles, lists and detail panels. The IDs stay the primary keys. Operations, process steps, routing operations, quality specifications, inspection results and shifts keep their IDs, as many of them share a name.
- Upgrading from 0.1.11 means uninstalling 0.1.11 first. The 50 existing bkn-eval answers are unchanged.
