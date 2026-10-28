# 0.1.10: clearer supply planning guidance and scenario experience cards

The 23 scenario cards now explain the business purpose for production planning and purchasing managers: checking supply, identifying shortages, tracing affected products and confirming delivery risks. Their questions, reference answers, page placement and Cypher are unchanged from 0.1.9 and remain aligned with the answer set dated 2026-08-25.

Where_Used reads parent materials in batches to reduce repeated lookups on large BOMs. Tool guidance clarifies identifiers and demand input structure, and the blind question paper removes calculation hints. Business rules, data, metric definitions and reference answers are unchanged. This release includes the fixes merged in #212.

The experience set ships in this package and is stored in the sample service installation record after successful installation. It requires the `sample.experience-set` capability. Updating a function in an existing knowledge network does not update its cards. Follow the existing uninstall/install workflow to replace an installed package; uninstall removes the sample's data and owned resources, so preserve any required changes first. Release acceptance evidence is recorded separately; model answer accuracy is not guaranteed by these changes.
