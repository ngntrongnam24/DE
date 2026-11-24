ARG SPARK_IMAGE=apache/spark:3.5.5
FROM ${SPARK_IMAGE}

# apache/spark image chay tren Ubuntu 20.04 voi Python 3.8 mac dinh, trong khi driver
# (Airflow, deploy-mode client) dung Python 3.12 -> PySpark bat buoc driver/executor
# phai khop minor version Python nen can cai them Python 3.12 cho worker.
#
# Khong dung deadsnakes PPA: tren Ubuntu 20.04/arch hien tai PPA khong co goi python3.12
# dung nghia, apt lai fallback coi "python3.12" nhu regex va cai nham goi khong lien quan
# (postgresql-plpython3-12). Build thang tu source cua python.org cho chac chan.
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential zlib1g-dev libssl-dev libffi-dev libbz2-dev \
       libreadline-dev libsqlite3-dev liblzma-dev wget ca-certificates \
    && wget -q https://www.python.org/ftp/python/3.12.4/Python-3.12.4.tgz \
    && tar xf Python-3.12.4.tgz \
    && cd Python-3.12.4 \
    && ./configure --prefix=/usr/local --enable-optimizations --with-ensurepip=no \
    && make -j"$(nproc)" \
    && make altinstall \
    && cd .. \
    && rm -rf Python-3.12.4 Python-3.12.4.tgz \
    && apt-get purge -y build-essential wget \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PYSPARK_PYTHON=/usr/local/bin/python3.12

USER spark
