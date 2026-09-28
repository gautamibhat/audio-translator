FROM apache/airflow:3.3.2-python3.12

USER root

RUN apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
        msodbcsql18 \
        unixodbc \
        unixodbc-dev \
        ffmpeg \
        g++ \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements-airflow.txt /tmp/requirements-airflow.txt

RUN pip install --no-cache-dir \
    "apache-airflow==3.3.2" \
    -r /tmp/requirements-airflow.txt
