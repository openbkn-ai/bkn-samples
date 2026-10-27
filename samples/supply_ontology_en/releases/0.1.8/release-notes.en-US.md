# 0.1.8: distinguish material classification fields

Clarify `group_name` (Stock Category) and `group_type` (Material Category), preventing the two classifications from being conflated in a lead-time answer. This fix changes no field names, display names, mappings, data or lead-time calculations. Source includes a separate MF-01 acceptance case; evaluation questions and gold answers are excluded from the installation package.

This package uses supply-chain main including #204 and the product's shared MariaDB, requiring OpenBKN >=0.2.1 <0.3.0. Other differences from previously installed versions require whole-package acceptance; field unit tests alone do not establish compatibility. The shortage rule requires separately configured event projection and trusted App Spec mappings. This classification regression does not claim Workshop integration acceptance.

A new version does not overwrite an existing network. Preserve and review customizations before an authorized maintainer explicitly updates these two descriptions and reads them back. Replacing the whole package uses the existing uninstall/install workflow; uninstall removes this sample's data and owned resources. Installation retry is not a metadata update. Actual acceptance is recorded separately with release evidence; this note does not promise correctness for every model answer.

Also shorten the not-yet-released replenishment-draft Action ID to at most 40 characters, updating its definition, binding, result reference and verification together. This sample identifier works with existing test deployments and current main; platform ID rules and replenishment logic are unchanged.

Omit the unused `value: null` constant on the draft Action input parameter, matching backend readback so ownership validation does not reject its own import. Parameter and tool binding checks remain strict.

Accept successful empty raw PUT-update responses in the function registration script. List reads and nonempty responses still require valid JSON and failed commands still raise errors, avoiding a failed installation after a successful first binding.
