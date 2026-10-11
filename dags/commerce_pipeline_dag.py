"""
Commerce Analytics Pipeline DAG

Schedule: Daily at midnight UTC
Flow: mutate_data -> ingest_to_warehouse -> dbt_snapshot -> dbt_build -> elementary_report

All steps use BashOperator. Commands run directly inside the Airflow container
where dbt, dlt, and all dependencies are pre-installed.
"""

from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow import DAG

PROJECT_ROOT = "/opt/airflow"
DBT_DIR = f"{PROJECT_ROOT}/dbt_project"

default_args = {
    "owner": "analytics_engineering",
    "retries": 1,
}

with DAG(
    dag_id="commerce_analytics_pipeline",
    default_args=default_args,
    description="Full e-commerce analytics pipeline: mutate, ingest, snapshot, build, report",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["commerce", "dbt", "analytics"],
) as dag:

    mutate_data = BashOperator(
        task_id="mutate_source_data",
        bash_command=f"cd {PROJECT_ROOT}/data_generator && python mutate.py",
    )

    ingest = BashOperator(
        task_id="ingest_to_warehouse",
        bash_command="cd /opt/airflow/ingestion && python load_to_warehouse.py",
    )

    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=f"cd {DBT_DIR} && dbt snapshot",
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"cd {DBT_DIR} && dbt build --fail-fast",
    )

    elementary_report = BashOperator(
        task_id="elementary_report",
        bash_command=f"cd {DBT_DIR} && edr report",
    )

    mutate_data >> ingest >> dbt_snapshot >> dbt_build >> elementary_report
