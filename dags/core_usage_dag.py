from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.utils.dates import days_ago
from datetime import timedelta

# Default args
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='core_usage_dag',
    default_args=default_args,
    description='ETL for SpaceX core usage data',
    schedule_interval='@daily',
    start_date=days_ago(1),
    catchup=False,
    tags=['spacex', 'etl'],
) as dag:

    run_etl = KubernetesPodOperator(
        task_id='run_etl',
        name='run-etl-pod',
        namespace='airflow',
        image='spacex-etl:latest',
        image_pull_policy='IfNotPresent',
        env_vars={
            'PG_HOST': 'postgres.data-platform.svc.cluster.local',
            'PG_PORT': '5432',
            'PG_DATABASE': 'spacexdb',
            'PG_USER': 'admin',
            'PG_PASSWORD': 'postgres_pass',
        },
        get_logs=True,
    )