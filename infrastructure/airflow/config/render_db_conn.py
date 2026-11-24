import os
from urllib.parse import quote_plus

user = quote_plus(os.environ["AIRFLOW_DB_USER"])
password = quote_plus(os.environ["AIRFLOW_DB_PASSWORD"])
db = os.environ["AIRFLOW_DB"]

print(f"postgresql+psycopg2://{user}:{password}@postgres:5432/{db}", end="")
