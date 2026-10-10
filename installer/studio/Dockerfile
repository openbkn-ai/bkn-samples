FROM python:3.12-slim AS python-base

FROM node:22-bookworm-slim AS cli
# Bootstrap HTTPS apt using the existing Python base's trusted CA bundle.
COPY --from=python-base /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
# npm still publishes 0.1.5. This platform rejects that CLI, so build the 0.2.0 commit.
ARG BKN_SDK_REF=703921dbd2affd39c07c65f65e05b4ae0f266187
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=3 update \
    && apt-get -o Acquire::Retries=3 install -y --no-install-recommends ca-certificates git \
    && git init /tmp/bkn-sdk \
    && git -C /tmp/bkn-sdk fetch --depth 1 https://github.com/openbkn-ai/bkn-sdk.git ${BKN_SDK_REF} \
    && git -C /tmp/bkn-sdk checkout FETCH_HEAD \
    && npm ci --prefix /tmp/bkn-sdk \
    && npm run build --prefix /tmp/bkn-sdk \
    && mkdir -p /opt/sdk-pack \
    && npm pack /tmp/bkn-sdk --pack-destination /opt/sdk-pack \
    && npm install -g /opt/sdk-pack/openbkn-bkn-sdk-*.tgz \
    && rm -rf /var/lib/apt/lists/* /tmp/bkn-sdk /opt/sdk-pack

FROM python-base

ARG TARGETARCH
ARG KUBECTL_VERSION=v1.32.2

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=3 update \
    && apt-get -o Acquire::Retries=3 install -y --no-install-recommends bash curl ca-certificates jq \
    && curl -fsSL -o /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
    && chmod 755 /usr/local/bin/kubectl \
    && python3 -m pip install --break-system-packages --no-cache-dir \
        "PyYAML>=6" "SQLAlchemy>=2" "PyMySQL>=1.1" "psycopg[binary]>=3.1" "jsonschema>=4.18,<5" \
    && rm -rf /var/lib/apt/lists/*

COPY --from=cli /usr/local/bin/node /usr/local/bin/node
COPY --from=cli /usr/local/lib/node_modules/@openbkn /usr/local/lib/node_modules/@openbkn
RUN ln -sf ../lib/node_modules/@openbkn/bkn-sdk/dist/cli.js /usr/local/bin/openbkn

WORKDIR /opt/bkn-samples
COPY installer /opt/bkn-samples/installer
COPY protocol/draft/schemas /opt/bkn-samples/protocol/draft/schemas
COPY samples /opt/bkn-samples/samples
COPY VERSION /opt/bkn-samples/VERSION
COPY manifest-index.json /opt/bkn-samples/manifest-index.json
ENV PYTHONPATH=/opt/bkn-samples
EXPOSE 8080
CMD ["python3", "-m", "installer.studio_http"]
