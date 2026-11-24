ARG SUPERSET_IMAGE=apache/superset:3.1.0
FROM ${SUPERSET_IMAGE}

USER root
RUN pip install --no-cache-dir trino sqlalchemy-trino
USER superset
