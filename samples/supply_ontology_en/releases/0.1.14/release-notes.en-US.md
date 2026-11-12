# 0.1.14: link production plans to their products

Based on 0.1.13, adds one relation, "Production Plan Product" (`supply_ontology_en_mps2prod`), matching a production plan's material code to the product code. Relations go from 14 to 15; objects, business data, functions and Skills are unchanged. This applies the Chinese 0.1.19 change to the English sample.

Production plans used to reach products only through demand forecasts, which few plans carry and which can cover several products. The new relation links every production plan directly to the product it makes, so scheduling, material readiness and purchase-date follow-ups can go production plan → product → BOM → material.

Existing installations keep their version; changing versions follows the standard uninstall/install flow after preserving required data and edits. Uninstall removes sample-owned data and resources; no in-place migration is provided.

Local model and data contract checks are not package acceptance: the fixed candidate still needs a fresh installation. These notes do not mean the version is published or installed on 8081.
