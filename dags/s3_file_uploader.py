import boto3
from datetime import timedelta
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago


s3 = boto3.resource('s3')

def s3_uploader(file_name, object_name, bucket):
    s3.Bucket(bucket).upload_file(file_name, object_name)


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(2),
    'email': ['abhishek_ku@yahoo.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG('S3_file_uploader',
          default_args=default_args,
          schedule_interval='@once',
          tags=['example']   ) as dag:

    start_task = DummyOperator(
            task_id='dummy_start'
    )


    upload_to_S3_task = PythonOperator(
             task_id='upload_to_S3',
             python_callable=s3_uploader,
             op_kwargs={
                    'file_name': '/tmp/input/tweet.json',
                    'object_name': 'landing/tweet.json',
                    'bucket': 'aktechthoughts',
             },
             dag=dag
    )

    start_task >> upload_to_S3_task

