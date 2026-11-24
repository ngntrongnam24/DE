"""Test doc tang silver, aggregate don gian, ghi sang tang gold tren Iceberg/MinIO."""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def build_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("test_gold_connectivity")
        .config("spark.jars.packages",
                "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.1,"
                "org.apache.iceberg:iceberg-aws-bundle:1.6.1,"
                "org.apache.hadoop:hadoop-aws:3.3.4,"
                "com.amazonaws:aws-java-sdk-bundle:1.12.620,"
                "com.oracle.database.jdbc:ojdbc11:23.4.0.24.05")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.lakehouse", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.lakehouse.catalog-impl", "org.apache.iceberg.rest.RESTCatalog")
        .config("spark.sql.catalog.lakehouse.uri", "http://iceberg-rest:8181")
        .config("spark.sql.catalog.lakehouse.warehouse", "s3://warehouse/")
        .config("spark.sql.catalog.lakehouse.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.catalog.lakehouse.s3.endpoint", "http://minio:9000")
        .config("spark.sql.catalog.lakehouse.s3.path-style-access", "true")
        .config("spark.sql.catalog.lakehouse.s3.region", "us-east-1")
        .config("spark.sql.catalog.lakehouse.client.region", "us-east-1")
        .config("spark.sql.catalog.lakehouse.s3.access-key-id", "minioadmin")
        .config("spark.sql.catalog.lakehouse.s3.secret-access-key", "aA@123456")
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.secret.key", "aA@123456")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.endpoint.region", "us-east-1")
        .getOrCreate()
    )


def test_read_silver(spark):
    print(">>> [1/2] Doc bang lakehouse.silver.test_connectivity")
    df = spark.table("lakehouse.silver.test_connectivity")
    df.show()
    return df


def test_write_gold(spark, silver_df):
    print(">>> [2/2] Aggregate va ghi sang lakehouse.gold.test_connectivity")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.gold")
    gold_df = (
        silver_df
        .groupBy("status_std")
        .agg(
            F.count("*").alias("total_count"),
            F.max("loaded_at").alias("last_loaded_at"),
        )
    )
    gold_df.writeTo("lakehouse.gold.test_connectivity").createOrReplace()
    spark.table("lakehouse.gold.test_connectivity").show()


if __name__ == "__main__":
    spark = build_spark()
    try:
        silver_df = test_read_silver(spark)
        test_write_gold(spark, silver_df)
        print(">>> TAT CA TEST PASS")
    finally:
        spark.stop()
