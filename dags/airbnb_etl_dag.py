from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'assem',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    'airbnb_etl_pipeline',
    default_args=default_args,
    description='End-to-End ETL for Airbnb Data',
    schedule_interval='@daily',
    catchup=False,
) as dag:

    task_staging = BashOperator(
        task_id='run_staging_layer',
        bash_command='cd /opt/airflow && python src/staging/load_staging.py',
    )

    task_dwh = BashOperator(
        task_id='run_data_warehouse_layer',
        bash_command='cd /opt/airflow && python src/warehouse/load_dwh.py',
    )

    task_staging >> task_dwh