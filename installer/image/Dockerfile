FROM python:3.12-slim AS certificates

FROM mariadb:11.4.7
COPY --from=certificates /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

RUN for source in /etc/apt/sources.list /etc/apt/sources.list.d/*; do \
        if [ -f "$source" ]; then \
            sed -i -e 's|http://ports.ubuntu.com|https://ports.ubuntu.com|g' \
                -e 's|http://archive.ubuntu.com|https://archive.ubuntu.com|g' \
                -e 's|http://security.ubuntu.com|https://security.ubuntu.com|g' "$source"; \
        fi; \
    done \
    && apt-get -o Acquire::Retries=3 update \
    && apt-get -o Acquire::Retries=3 install -y --no-install-recommends python3 python3-pip \
    && python3 -m pip install --break-system-packages --no-cache-dir \
        "PyYAML>=6" "SQLAlchemy>=2" "PyMySQL>=1.1" "psycopg[binary]>=3.1" \
    && rm -rf /var/lib/apt/lists/*

COPY VERSION /opt/bkn-samples/VERSION
COPY manifest-index.json /opt/bkn-samples/manifest-index.json
COPY samples/supply_ontology_hand/data /opt/bkn-samples/samples/supply_ontology_hand/data
COPY samples/supply_ontology_hand/tools /opt/bkn-samples/samples/supply_ontology_hand/tools
COPY samples/supply_ontology_hand/db /opt/bkn-samples/samples/supply_ontology_hand/db
COPY samples/supply_ontology_hand/sample.yaml /opt/bkn-samples/samples/supply_ontology_hand/sample.yaml
COPY samples/world-cup/dataset.lock /opt/bkn-samples/samples/world-cup/dataset.lock
COPY samples/world-cup/db /opt/bkn-samples/samples/world-cup/db
COPY samples/world-cup/sample.yaml /opt/bkn-samples/samples/world-cup/sample.yaml
COPY installer/image/10-bkn-sample-init.sh /docker-entrypoint-initdb.d/10-bkn-sample-init.sh
COPY installer/image/select_sample_init.py /docker-entrypoint-initdb.d/select_sample_init.py

RUN chmod 755 /docker-entrypoint-initdb.d/10-bkn-sample-init.sh \
    /opt/bkn-samples/samples/supply_ontology_hand/db/init.sh \
    /opt/bkn-samples/samples/supply_ontology_hand/db/verify.sh \
    /opt/bkn-samples/samples/world-cup/db/init.sh \
    /opt/bkn-samples/samples/world-cup/db/verify.sh
