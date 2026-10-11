.PHONY: up down seed pipeline logs clean

# Start all services
up:
	docker-compose up -d
	@echo "Waiting for Postgres to be healthy..."
	@sleep 10
	@echo "Services running. Airflow UI at http://localhost:8080"

# Stop all services
down:
	docker-compose down

# Seed source data (run once)
seed:
	docker-compose exec airflow-scheduler bash -c "cd /opt/airflow/data_generator && python generate.py"

# Run the full pipeline manually
pipeline:
	docker-compose exec airflow-scheduler bash -c "cd /opt/airflow/data_generator && python mutate.py"
	docker-compose exec airflow-scheduler bash -c "cd /opt/airflow && python ingestion/load_to_warehouse.py"
	docker-compose exec airflow-scheduler bash -c "cd /opt/airflow/dbt_project && dbt deps && dbt seed && dbt snapshot && dbt build --fail-fast"

# View Airflow logs
logs:
	docker-compose logs -f airflow-scheduler

# Full reset
clean:
	docker-compose down -v
	@echo "All volumes removed. Run 'make up' then 'make seed' to start fresh."
