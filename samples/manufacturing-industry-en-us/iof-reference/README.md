# IOF Core and Production Planning Complete Reference

## Upstream open-source source

This reference layer is derived from the [Industrial Ontologies Foundry ontology repository](https://github.com/iofoundry/ontology), using its [IOF Core](https://spec.industrialontologies.org/portal/release/202603/core.html) and [Production Planning module](https://spec.industrialontologies.org/portal/release/202603/productionplanning/ProductionPlanningOntology.html) as the fixed upstream scope. IOF declares the Core source under the [MIT license](https://github.com/iofoundry/Core/blob/main/Core.rdf). Source IRIs in this package remain the authoritative term-level trace.

This directory is the complete IOF standards layer within the manufacturing industry sample. It covers every named class and named object property in the fixed IOF source files: 91 IOF Core class declarations, 22 Production Planning declarations (112 unique class IRIs), 83 Core properties, and 4 Production Planning properties (85 unique property IRIs). A BKN RelationType is generated only when its explicit direct domain and range are each one named class in these fixed modules. The remaining properties are retained in [the unprojected OWL property inventory](docs/unprojected-owl-relations.md), rather than being attached to a made-up catch-all object.

The source RDF also contains 14 anonymous Core and 8 anonymous Production Planning `owl:Class` restriction expressions. They have no independent IRI, label, or separately bindable instance type, so they are not generated as BKN ObjectTypes. Their constraint semantics remain in the source RDF and are described in the semantic-differences document.

`kn/` is an offline-validatable BKN directory. Each named class becomes an ObjectType. The `data/` directory has one traceable synthetic reference-instance CSV for every one of the 112 ObjectTypes; it demonstrates full import coverage, rather than claiming that every IOF class is a real operational record. Every ObjectType retains `source_iri`, `source_label`, and `source_definition` for traceability. The seven direct BKN relations are linked in the reference instances through `*_target_id` fields. Run `python3 tools/verify_reference_instances.py` to verify the coverage and links.

The parent `kn/` directory is the 40-object end-to-end manufacturing operations model. It supplies operational data for demand, supply, inventory, production, quality, workforce, and maintenance; it does not replace this complete standards layer.
