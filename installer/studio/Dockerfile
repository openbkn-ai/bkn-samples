FROM node:22-bookworm-slim AS cli
RUN npm install -g @openbkn/bkn-sdk@0.2.0

FROM python:3.12-slim

ARG TARGETARCH
ARG KUBECTL_VERSION=v1.32.2

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL -o /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
    && chmod 755 /usr/local/bin/kubectl \
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
