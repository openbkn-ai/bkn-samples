FROM python:3.12-slim

ARG TARGETARCH
ARG KUBECTL_VERSION=v1.32.2

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL -o /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
    && chmod 755 /usr/local/bin/kubectl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/bkn-samples
COPY installer /opt/bkn-samples/installer
COPY samples /opt/bkn-samples/samples
COPY VERSION /opt/bkn-samples/VERSION
COPY manifest-index.json /opt/bkn-samples/manifest-index.json
ENV PYTHONPATH=/opt/bkn-samples
EXPOSE 8080
CMD ["python3", "-m", "installer.studio_http"]

COPY installer /opt/bkn-samples/installer
COPY samples /opt/bkn-samples/samples
COPY VERSION /opt/bkn-samples/VERSION
COPY manifest-index.json /opt/bkn-samples/manifest-index.json
ENV PYTHONPATH=/opt/bkn-samples
EXPOSE 8080
CMD ["python3", "-m", "installer.studio_http"]
