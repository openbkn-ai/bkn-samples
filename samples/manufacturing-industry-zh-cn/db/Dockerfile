FROM ghcr.io/openbkn-ai/bkn-samples@sha256:805317bc1ac93e58f4149e35a7a0a75057330d8888ca54526a354996f313fcd1
COPY data/ /opt/bkn-samples/samples/manufacturing-industry-zh-cn/data/
COPY db/ /opt/bkn-samples/samples/manufacturing-industry-zh-cn/db/
COPY sample.yaml dataset.lock /opt/bkn-samples/samples/manufacturing-industry-zh-cn/
RUN chmod 755 /opt/bkn-samples/samples/manufacturing-industry-zh-cn/db/init.sh /opt/bkn-samples/samples/manufacturing-industry-zh-cn/db/verify.sh
