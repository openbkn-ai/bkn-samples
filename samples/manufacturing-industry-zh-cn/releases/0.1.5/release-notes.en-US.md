# 0.1.5: data rebuilt from one business story, role Skills and experience cards added

This release follows the new [business PRD](../../docs/PRD.md). Tables and columns are unchanged, and the data now tell one coherent business story: machines, operators, materials, suppliers and stock at the two plants are shared across work orders, with deliberate exceptions such as late and split shipments, scrap, rejected and remade work orders, a quality escape, non-compliant executions, an issue from a receipt in inspection, short and rejected purchases, a draft BOM and overdue maintenance.

Adds two Skills, "Orders and materials" and "Production and quality", stating the business rules and Cypher patterns; the rules are also written into the knowledge network description. The sample ships no functions or metrics, so the Community edition can use all of it. The earlier 100-question bank depended on the old data and is replaced by the new 50-question business-scenario test set; 15 experience cards are added.

Follow the existing uninstall/install workflow to replace an installed package; uninstall removes the sample's data and owned resources, so preserve any required changes first. Acceptance results are recorded separately and do not guarantee model answer accuracy.
