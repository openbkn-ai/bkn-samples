# Local acceptance data image. Build from the repository root.
# The standard selector discovers this sample from its manifest.
FROM ghcr.io/openbkn-ai/bkn-samples@sha256:805317bc1ac93e58f4149e35a7a0a75057330d8888ca54526a354996f313fcd1
COPY samples/supply_ontology_en/data /opt/bkn-samples/samples/supply_ontology_en/data
COPY samples/supply_ontology_en/tools /opt/bkn-samples/samples/supply_ontology_en/tools
COPY samples/supply_ontology_en/db /opt/bkn-samples/samples/supply_ontology_en/db
COPY samples/supply_ontology_en/sample.yaml samples/supply_ontology_en/dataset.lock /opt/bkn-samples/samples/supply_ontology_en/
RUN chmod 755 /opt/bkn-samples/samples/supply_ontology_en/db/init.sh \
    /opt/bkn-samples/samples/supply_ontology_en/db/verify.sh
