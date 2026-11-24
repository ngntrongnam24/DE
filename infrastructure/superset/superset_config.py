import os

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY")

# DATABASE_PASSWORD phai la gia tri da url-encode san (xem SUPERSET_DB_PASSWORD_URLENC trong .env)
SQLALCHEMY_DATABASE_URI = (
    "postgresql+psycopg2://"
    f"{os.environ.get('DATABASE_USER')}:{os.environ.get('DATABASE_PASSWORD')}"
    f"@{os.environ.get('DATABASE_HOST')}:{os.environ.get('DATABASE_PORT')}"
    f"/{os.environ.get('DATABASE_DB')}"
)

FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
}
