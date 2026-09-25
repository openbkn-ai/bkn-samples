FROM python:3.12-slim

WORKDIR /opt/bkn-samples
COPY installer /opt/bkn-samples/installer
COPY samples /opt/bkn-samples/samples
COPY VERSION /opt/bkn-samples/VERSION
COPY manifest-index.json /opt/bkn-samples/manifest-index.json
ENV PYTHONPATH=/opt/bkn-samples
EXPOSE 8080
CMD ["python3", "-m", "installer.studio_http"]
