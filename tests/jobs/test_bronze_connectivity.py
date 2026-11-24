"""Test ket noi Spark <-> Iceberg (MinIO) va Spark <-> Oracle truoc khi viet job ingest bronze thuc."""

from pyspark.sql import SparkSession


def build_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("test_bronze_connectivity")
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


def test_sql_sanity(spark):
    print(">>> [1/3] Spark SQL co ban")
    spark.sql("SELECT 1 AS test_col").show()


def test_iceberg_write_read(spark):
    print(">>> [2/3] Ghi/doc Iceberg tren MinIO (namespace bronze)")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.bronze")
    df = spark.createDataFrame([(1, "ok"), (2, "ok")], ["id", "status"])
    df.writeTo("lakehouse.bronze.test_connectivity").createOrReplace()
    spark.table("lakehouse.bronze.test_connectivity").show()


def test_oracle_jdbc(spark):
    print(">>> [3/3] Ket noi JDBC toi Oracle")
    df = (
        spark.read.format("jdbc")
        .option("url", "jdbc:oracle:thin:@oracle-db:1521/XEPDB1")
        .option("driver", "oracle.jdbc.OracleDriver")
        .option("dbtable", "(SELECT 1 AS test_col FROM DUAL)")
        .option("user", "lakehouse")
        .option("password", "aA@123456")
        .load()
    )
    df.show()


if __name__ == "__main__":
    spark = build_spark()
    try:
        test_sql_sanity(spark)
        test_iceberg_write_read(spark)
        test_oracle_jdbc(spark)
        print(">>> TAT CA TEST PASS")
    finally:
        spark.stop()
