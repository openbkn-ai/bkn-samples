FROM python:3.12-slim

WORKDIR /opt/bkn-samples
COPY installer /opt/bkn-samples/installer
COPY VERSION /opt/bkn-samples/VERSION
ENV PYTHONPATH=/opt/bkn-samples
EXPOSE 8080
CMD ["python3", "-m", "installer.studio_http"]
