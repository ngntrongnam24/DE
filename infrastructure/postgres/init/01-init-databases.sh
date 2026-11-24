#!/bin/bash
set -e

create_user_and_database() {
  local database=$1
  local user=$2
  local password=$3

  echo "Tao user '$user' va database '$database'..."

  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_USER" <<-EOSQL
    DO
    \$\$
    BEGIN
      IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$user') THEN
        CREATE USER "$user" WITH PASSWORD '$password';
      END IF;
    END
    \$\$;
EOSQL

  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE "$database" OWNER "$user"'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
EOSQL
}

create_user_and_database "$AIRFLOW_DB" "$AIRFLOW_DB_USER" "$AIRFLOW_DB_PASSWORD"
create_user_and_database "$SUPERSET_DB" "$SUPERSET_DB_USER" "$SUPERSET_DB_PASSWORD"
create_user_and_database "$ICEBERG_CATALOG_DB" "$ICEBERG_CATALOG_DB_USER" "$ICEBERG_CATALOG_DB_PASSWORD"

echo "Da tao xong database: $AIRFLOW_DB, $SUPERSET_DB, $ICEBERG_CATALOG_DB"
