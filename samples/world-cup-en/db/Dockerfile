# Sample data image. Build from the repository root.
# Include only the locked data and database hooks required by the standard selector.
FROM ghcr.io/openbkn-ai/bkn-samples@sha256:805317bc1ac93e58f4149e35a7a0a75057330d8888ca54526a354996f313fcd1
COPY samples/world-cup-en/data /opt/bkn-samples/samples/world-cup-en/data
COPY samples/world-cup-en/db /opt/bkn-samples/samples/world-cup-en/db
COPY samples/world-cup-en/sample.yaml samples/world-cup-en/dataset.lock /opt/bkn-samples/samples/world-cup-en/
RUN chmod 755 /opt/bkn-samples/samples/world-cup-en/db/init.sh \
    /opt/bkn-samples/samples/world-cup-en/db/verify.sh
