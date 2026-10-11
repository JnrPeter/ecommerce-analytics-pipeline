FROM apache/airflow:3.0.1-python3.12

USER root

# System dependencies for psycopg2 and duckdb
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy project files (done via docker-compose volumes, but profiles.yml needs to be
# available at ~/.dbt for Elementary's edr command)
COPY --chown=airflow:root dbt_project/profiles.yml /home/airflow/.dbt/profiles.yml