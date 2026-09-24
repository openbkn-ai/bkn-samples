ARG MARIADB_IMAGE=mariadb:11.4.7
FROM ${MARIADB_IMAGE}

RUN find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) \
      -exec sed -i \
        -e 's|http://|https://|g' \
        -e 's|https://security.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g' {} + \
    && apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-venv curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/bkn-samples
COPY samples/supply_ontology_hand/data/ samples/supply_ontology_hand/data/
COPY samples/supply_ontology_hand/tools/requirements.txt samples/supply_ontology_hand/tools/requirements.txt
COPY samples/supply_ontology_hand/tools/load_sample_data.py samples/supply_ontology_hand/tools/load_sample_data.py
COPY samples/supply_ontology_hand/tools/mapping/ samples/supply_ontology_hand/tools/mapping/
COPY samples/supply_ontology_hand/db/ samples/supply_ontology_hand/db/
COPY samples/world-cup/scripts/worldcup_dataset_stems.inc.sh samples/world-cup/scripts/worldcup_dataset_stems.inc.sh
COPY samples/world-cup/db/ samples/world-cup/db/
COPY samples/world-cup/dataset.lock samples/world-cup/dataset.lock
COPY docker/entrypoint.sh /usr/local/bin/bkn-samples-entrypoint
COPY docker/init.sh /docker-entrypoint-initdb.d/10-bkn-sample-init.sh
COPY docker/healthcheck.sh /opt/bkn-samples/bin/healthcheck

RUN python3 -m venv /opt/bkn-samples/.venv \
    && /opt/bkn-samples/.venv/bin/pip install --no-cache-dir --retries 5 --timeout 120 \
      -r samples/supply_ontology_hand/tools/requirements.txt \
    && chmod 0755 /usr/local/bin/bkn-samples-entrypoint /docker-entrypoint-initdb.d/10-bkn-sample-init.sh /opt/bkn-samples/bin/healthcheck \
    && find samples -path '*/db/*.sh' -exec chmod 0755 {} +

ENV PATH="/opt/bkn-samples/.venv/bin:${PATH}"

HEALTHCHECK --interval=5s --timeout=5s --start-period=10s --retries=60 \
  CMD ["/opt/bkn-samples/bin/healthcheck"]

ENTRYPOINT ["/usr/local/bin/bkn-samples-entrypoint"]
CMD ["mariadbd", "--datadir=/var/lib/bkn-samples/mysql"]
