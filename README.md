# E-commerce Analytics Pipeline

An end-to-end analytics engineering project: data generation, incremental ingestion, SCD-tracked dimensions, automated quality monitoring, and daily orchestration, fully containerized with Docker Compose.

One command to run the entire stack:

```bash
docker-compose up -d --build
```

## Architecture

```
PostgreSQL (source) --> dlt (ingestion) --> DuckDB (warehouse) --> dbt (transformation) --> Marts (analytics)
```

**Schemas in DuckDB:**

| Schema | Owner | Purpose |
|-----------|-------|---------|
| raw | dlt | Source tables synced from PostgreSQL |
| staging | dbt | Cleaned views (1:1 with raw, renamed + retyped) |
| snapshots | dbt | Versioned history for SCD tracking |
| marts | dbt | Dimensions + facts (what analysts query) |

## Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Infrastructure | Docker Compose (5 services) | Postgres, Airflow api-server, scheduler, dag-processor, init |
| Source database | PostgreSQL 16 | Operational data store |
| Data generation | Python (Faker) | Seed + mutation scripts (240 realistic product names, 8 categories) |
| Ingestion | dlt | Incremental merge from Postgres to DuckDB with schema contracts |
| Warehouse | DuckDB | Analytical storage (persisted via Docker volume) |
| Transformation | dbt | Staging, intermediate, snapshots, marts (5 staging, 2 intermediate, 3 snapshots, 3 dims, 5 facts) |
| Data quality | dbt tests + dbt_expectations | 64 tests: uniqueness, nulls, ranges, accepted values |
| Anomaly detection | Elementary + edr | Volume anomalies, freshness, schema changes, HTML dashboard |
| Orchestration | Airflow 3.0.1 | Daily pipeline: mutate > ingest > snapshot > build > report |
| CI/CD | GitHub Actions | Full pipeline test on every PR |

## Getting started

**Prerequisites:** Docker and Docker Compose.

```bash
# Clone the repo
git clone https://github.com/JnrPeter/ecommerce-analytics-pipeline.git
cd ecommerce-analytics-pipeline

# Build and start everything
docker-compose up -d --build

# Open the Airflow UI
# http://localhost:8080
# The DAG "commerce_analytics_pipeline" is ready to trigger.
```

On first run, you need to generate the initial source data:

```bash
docker-compose exec airflow-scheduler bash -c "python /opt/airflow/data_generator/generate.py"
```

After that, trigger the DAG from the Airflow UI or wait for the @daily schedule.

## Docker Compose services

The containerized stack runs 5 services. Airflow 3.x requires separate processes for the API server, scheduler, and DAG processor.

| Service | Role | Port |
|---------|------|------|
| postgres | Source database + Airflow metadata | 5433 |
| airflow-api-server | Web UI + REST API | 8080 |
| airflow-scheduler | Triggers and executes tasks | - |
| airflow-dag-processor | Parses DAG files (required in Airflow 3.x) | - |
| airflow-init | One-shot: runs `airflow db migrate` then exits | - |

All Airflow services share one custom image built from `apache/airflow:3.0.1-python3.12` with dbt-duckdb, dlt, elementary-data, and faker baked in.

## The daily pipeline

The DAG runs 5 tasks in sequence on a @daily schedule:

```
mutate_source_data > ingest_to_warehouse > dbt_snapshot > dbt_build > elementary_report
```

1. **mutate_source_data** generates daily changes to the source database (500 new orders, price changes, zone moves, tier upgrades)
2. **ingest_to_warehouse** incrementally syncs PostgreSQL to DuckDB using dlt (merge strategy, cursor-based loading)
3. **dbt_snapshot** captures SCD versions before transformations run (must run before build)
4. **dbt_build** runs all staging views, intermediate models, dimensions, fact tables, and 64 tests
5. **elementary_report** generates an HTML quality dashboard with anomaly detection

## dbt models

**Staging (5 views):** One per source table. Clean, rename, retype. No business logic.

**Intermediate (2 ephemeral models):** Join staging models and compute business logic like `delivery_delay_minutes` and `delivery_performance` (on_time / slightly_late / late / very_late).

**Dimensions (3 tables):**

| Table | SCD Type | Tracks |
|-------|----------|--------|
| dim_customers | Type 1 (overwrite) | Latest name, email, tier |
| dim_retailers | Type 2 (history) | Zone moves, status changes with valid_from/valid_to |
| dim_products | Type 2 (history) | Price changes with valid_from/valid_to |

**Facts (5 tables):**

| Table | Materialization | Key metrics |
|-------|----------------|-------------|
| fct_orders | Incremental (delete+insert) | subtotal, discount, delivery_fee, total_amount, rating, delivery_performance |
| fct_order_items | Incremental (delete+insert) | quantity, unit_price, line_total, product_category |
| fct_daily_zone_summary | Full rebuild | Revenue, avg order value, on-time %, cancellation rate per zone per day |
| fct_retailer_performance | Full rebuild | Revenue, avg rating, on-time %, items sold per retailer |
| fct_payment_channel_summary | Full rebuild | Revenue, avg order value per payment method + channel per day |

## Data quality

Three layers of defense:

1. **dlt schema contracts** catch upstream schema drift at ingestion (columns and types frozen)
2. **dbt tests + dbt_expectations** enforce known rules at transformation (64 tests)
3. **Elementary** detects unknown anomalies by learning baselines from run history (volume, freshness, schema changes)

Run `edr report` inside the container to generate the Elementary HTML dashboard.

## CI/CD

Every pull request to `main` triggers a GitHub Actions workflow that runs the full pipeline from scratch: Postgres service, data generation, dlt ingestion, dbt seed, snapshot, build, and docs generation. If anything breaks, the PR gets a red check.

## Useful commands

```bash
# Run dbt manually inside the container
docker-compose exec airflow-scheduler bash -c "cd /opt/airflow/dbt_project && dbt build --fail-fast"

# Copy DuckDB file to your local machine for querying
docker cp airflow_scheduler:/opt/airflow/commerce_ingestion.duckdb ./commerce_ingestion.duckdb

# View Airflow logs
docker-compose logs -f airflow-scheduler

# Stop everything
docker-compose down

# Stop and remove volumes (resets all data)
docker-compose down -v
```

## Project history

This project was built iteratively from a local-first setup. See the [development repo](https://github.com/JnrPeter/commerce-analytics-platform) for the full build history.