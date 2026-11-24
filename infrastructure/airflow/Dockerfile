ARG AIRFLOW_IMAGE=apache/airflow:2.9.3
FROM ${AIRFLOW_IMAGE}

# Can JVM de pyspark/spark-submit chay duoc tu container Airflow (deploy-mode client).
# Version 17 khop voi Spark 3.5.5 dang chay tren spark-master/spark-worker.
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER airflow

# Ghim apache-airflow de pip khong tu nang major version khi resolve provider.
RUN pip install --no-cache-dir \
    "apache-airflow==2.9.3" \
    "apache-airflow-providers-apache-spark==5.2.1" \
    "pyspark==3.5.5"
