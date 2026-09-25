FROM node:22-bookworm-slim AS cli
RUN npm install -g @openbkn/bkn-sdk@0.1.5

FROM python:3.12-slim

ARG TARGETARCH
ARG KUBECTL_VERSION=v1.32.2

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash curl ca-certificates jq \
    && curl -fsSL -o /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
    && chmod 755 /usr/local/bin/kubectl \
    && python3 -m pip install --break-system-packages --no-cache-dir "PyYAML>=6" \
    && rm -rf /var/lib/apt/lists/*

COPY --from=cli /usr/local/bin/node /usr/local/bin/node
COPY --from=cli /usr/local/lib/node_modules/@openbkn /usr/local/lib/node_modules/@openbkn
RUN ln -sf ../lib/node_modules/@openbkn/bkn-sdk/dist/cli.js /usr/local/bin/openbkn

WORKDIR /opt/bkn-samples
COPY installer /opt/bkn-samples/installer
COPY samples /opt/bkn-samples/samples
COPY VERSION /opt/bkn-samples/VERSION
COPY manifest-index.json /opt/bkn-samples/manifest-index.json
ENV PYTHONPATH=/opt/bkn-samples
EXPOSE 8080
CMD ["python3", "-m", "installer.studio_http"]
