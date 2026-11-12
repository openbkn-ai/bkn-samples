# 0.1.19: link production plans to their products

Based on 0.1.18, adds one relation, "生产计划关联产品" (`supply_ontology_hand_mps2prod`), matching a production plan's material code to the product code. Relations go from 14 to 15; objects, business data, functions and Skills are unchanged.

Production plans used to reach products only through demand forecasts: 19 of the 605 plans carry a forecast number, and one forecast can cover several products. The new relation links all 605 plans directly to the 29 products they make, so scheduling, material readiness and purchase-date follow-ups can go production plan → product → BOM → material.

Existing installations keep their version; changing versions follows the standard uninstall/install flow after preserving required data and edits. Uninstall removes sample-owned data and resources; no in-place migration is provided.

Local model and data contract checks are not package acceptance: the fixed candidate still needs a fresh installation. These notes do not mean the version is published or installed on 8081.
