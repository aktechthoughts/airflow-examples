import boto3
import time
from datetime import timedelta
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable

emr_config = Variable.get("emr_config", deserialize_json=True)

client = boto3.client('emr', region_name=emr_config['region'])


def create_cluster():
    response = client.run_job_flow(
        Name=emr_config['cluster-name'],
        ReleaseLabel=emr_config['emr-version'],
        Instances={
            'MasterInstanceType': emr_config['master-instance-type'],
            'SlaveInstanceType': emr_config['slave-instance-type'],
            'InstanceCount': int(emr_config['instance-count']),
            'KeepJobFlowAliveWhenNoSteps': bool(emr_config['keep-job-alive']),
            'TerminationProtected': bool(emr_config['termination-protected']),
            'Ec2SubnetId': emr_config['vpc-subnet-id'],
            'Ec2KeyName': emr_config['vpc-ec2-key'],
        },
        VisibleToAllUsers=True,
        JobFlowRole=emr_config['job-role'],
        ServiceRole=emr_config['service-role']
    )

    return response['ClusterArn'].split('/')[1]


def getClusterStatus(ClusterId):
    start_ms = int(round(time.time() * 1000))
    next_ms = start_ms

    while next_ms <= (start_ms + 600000):
        state = client.describe_cluster(ClusterId=ClusterId)['Cluster']['Status']['State']
        print(state)
        if state != 'WAITING':
            time.sleep(30)
            next_ms = int(round(time.time() * 1000))
        else:
            break

    return state

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

with DAG('emr_cluster_creator',
         default_args=default_args,
         schedule_interval='@once',
         tags=['example']) as dag:
    start_task = DummyOperator(
        task_id='dummy_start'
    )

    create_cluster_task = PythonOperator(
        task_id='create_cluster_task',
        python_callable=create_cluster,
        dag=dag
    )

    wait_for_cluster_task = PythonOperator(
        task_id='wait_for_cluster_task',
        python_callable=getClusterStatus,
        op_kwargs={
            'ClusterId': "{{ task_instance.xcom_pull(task_ids='create_cluster_task') }}"
        },
        dag=dag
    )

    start_task >> create_cluster_task >> wait_for_cluster_task
