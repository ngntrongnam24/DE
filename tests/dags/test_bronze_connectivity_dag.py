from datetime import datetime
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

with DAG(
    dag_id="test_bronze_connectivity",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["test"],
) as dag:
    submit_test_job = SparkSubmitOperator(
        task_id="submit_test_job",
        application="/opt/airflow/jobs/test_bronze_connectivity.py",
        conn_id="spark_default",
        deploy_mode="client",
        packages=(
            "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.1,"
            "org.apache.iceberg:iceberg-aws-bundle:1.6.1,"
            "org.apache.hadoop:hadoop-aws:3.3.4,"
            "com.amazonaws:aws-java-sdk-bundle:1.12.620,"
            "com.oracle.database.jdbc:ojdbc11:23.4.0.24.05"
        ),
        conf={
            "spark.driver.extraJavaOptions": "-Daws.region=us-east-1",
            "spark.executor.extraJavaOptions": "-Daws.region=us-east-1",
            "spark.pyspark.python": "/usr/local/bin/python3.12",
        },
    )

    submit_silver_test_job = SparkSubmitOperator(
        task_id="submit_silver_test_job",
        application="/opt/airflow/jobs/test_silver_connectivity.py",
        conn_id="spark_default",
        deploy_mode="client",
        packages=(
            "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.1,"
            "org.apache.iceberg:iceberg-aws-bundle:1.6.1,"
            "org.apache.hadoop:hadoop-aws:3.3.4,"
            "com.amazonaws:aws-java-sdk-bundle:1.12.620,"
            "com.oracle.database.jdbc:ojdbc11:23.4.0.24.05"
        ),
        conf={
            "spark.driver.extraJavaOptions": "-Daws.region=us-east-1",
            "spark.executor.extraJavaOptions": "-Daws.region=us-east-1",
            "spark.pyspark.python": "/usr/local/bin/python3.12",
        },
    )

    submit_gold_test_job = SparkSubmitOperator(
        task_id="submit_gold_test_job",
        application="/opt/airflow/jobs/test_gold_connectivity.py",
        conn_id="spark_default",
        deploy_mode="client",
        packages=(
            "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.1,"
            "org.apache.iceberg:iceberg-aws-bundle:1.6.1,"
            "org.apache.hadoop:hadoop-aws:3.3.4,"
            "com.amazonaws:aws-java-sdk-bundle:1.12.620,"
            "com.oracle.database.jdbc:ojdbc11:23.4.0.24.05"
        ),
        conf={
            "spark.driver.extraJavaOptions": "-Daws.region=us-east-1",
            "spark.executor.extraJavaOptions": "-Daws.region=us-east-1",
            "spark.pyspark.python": "/usr/local/bin/python3.12",
        },
    )

    submit_test_job >> submit_silver_test_job >> submit_gold_test_job
