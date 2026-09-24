FROM mariadb:11.4.7

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && python3 -m pip install --break-system-packages --no-cache-dir \
        "PyYAML>=6" "SQLAlchemy>=2" "PyMySQL>=1.1" "psycopg[binary]>=3.1" \
    && rm -rf /var/lib/apt/lists/*

COPY VERSION /opt/bkn-samples/VERSION
COPY samples/supply_ontology_hand/data /opt/bkn-samples/samples/supply_ontology_hand/data
COPY samples/supply_ontology_hand/tools /opt/bkn-samples/samples/supply_ontology_hand/tools
COPY samples/supply_ontology_hand/db /opt/bkn-samples/samples/supply_ontology_hand/db
COPY samples/supply_ontology_hand/sample.yaml /opt/bkn-samples/samples/supply_ontology_hand/sample.yaml
COPY installer/image/10-bkn-sample-init.sh /docker-entrypoint-initdb.d/10-bkn-sample-init.sh

RUN chmod 755 /docker-entrypoint-initdb.d/10-bkn-sample-init.sh \
    /opt/bkn-samples/samples/supply_ontology_hand/db/init.sh \
    /opt/bkn-samples/samples/supply_ontology_hand/db/verify.sh
