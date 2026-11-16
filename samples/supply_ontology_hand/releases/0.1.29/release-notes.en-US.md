# 0.1.29: kit checks complete with many plans

Based on 0.1.28. Business data, objects, relations, actions and the Kit Scheduling app are unchanged.

**Kit checks no longer fail with "rule tool error"**: when Workshop calls the kit check and the line check through the toolbox proxy, the functions page through the ontology query API with the cursor it returns instead of an offset. When the plans' materials match more than 10,000 stock records, the second page used to be refused and the whole batch showed "could not check"; all records are now read. The checks themselves are unchanged.

Existing installations keep their version; changing versions follows the standard uninstall/install flow, which removes sample-owned data and resources. No in-place migration is provided.
