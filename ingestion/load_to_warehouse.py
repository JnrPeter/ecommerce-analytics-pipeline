"""
dlt pipeline: PostgreSQL (source) -> DuckDB (warehouse).
Extracts all five source tables with incremental loading and merge write disposition.
Schema contract set to freeze columns and data types; tables can evolve on first run.
"""

import os
from datetime import datetime

import dlt
from dlt.sources.sql_database import sql_database
from dotenv import load_dotenv

load_dotenv()


def build_pipeline():
    pg_conn = (
        f"postgresql://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}"
        f"@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DATABASE')}"
    )

    source = sql_database(
        credentials=pg_conn,
        table_names=["customers", "retailers", "products", "orders", "order_items"],
    )

    source.schema_contract = {
        "tables": "evolve",
        "columns": "freeze",
        "data_type": "freeze",
    }

    source.customers.apply_hints(
        primary_key="customer_id",
        write_disposition="merge",
        incremental=dlt.sources.incremental(
            cursor_path="updated_at",
            initial_value=datetime(2020, 1, 1),
            row_order="asc",
        ),
    )

    source.retailers.apply_hints(
        primary_key="retailer_id",
        write_disposition="merge",
        incremental=dlt.sources.incremental(
            cursor_path="updated_at",
            initial_value=datetime(2020, 1, 1),
            row_order="asc",
        ),
    )

    source.products.apply_hints(
        primary_key="product_id",
        write_disposition="merge",
        incremental=dlt.sources.incremental(
            cursor_path="updated_at",
            initial_value=datetime(2020, 1, 1),
            row_order="asc",
        ),
    )

    source.orders.apply_hints(
        primary_key="order_id",
        write_disposition="merge",
        incremental=dlt.sources.incremental(
            cursor_path="created_at",
            initial_value=datetime(2020, 1, 1),
            row_order="asc",
        ),
    )

    source.order_items.apply_hints(
        primary_key="item_id",
        write_disposition="merge",
        incremental=dlt.sources.incremental(
            cursor_path="created_at",
            initial_value=datetime(2020, 1, 1),
            row_order="asc",
        ),
    )

    pipeline = dlt.pipeline(
        pipeline_name="commerce_ingestion",
        destination=dlt.destinations.duckdb("/opt/airflow/commerce_ingestion.duckdb"),
        dataset_name="raw",
    )

    return pipeline, source


def main():
    pipeline, source = build_pipeline()

    print(f"Loading to {pipeline.destination.destination_name}...")
    info = pipeline.run(source)
    print(info)
    print("Ingestion complete.")


if __name__ == "__main__":
    main()
