# Project DE — Hạ tầng Lakehouse

Hạ tầng Docker Compose cho dự án lakehouse: Oracle XE (nguồn OLTP mẫu), MinIO (object storage), PostgreSQL (metadata), Iceberg REST Catalog, Apache Spark (Master/Worker), Trino, Apache Airflow và Apache Superset.

## 1. Yêu cầu

- Docker Desktop (đã bật WSL2 backend trên Windows), kèm sẵn Docker Compose.
- RAM trống tối thiểu khoảng 8GB.

## 2. Cài đặt lần đầu sau khi clone

```bash
git clone <url-repo-cua-ban>
cd project-de
cp .env.example .env
```

Mở file `.env` vừa tạo, đổi toàn bộ giá trị `changeme` thành password của bạn (mỗi service một password khác nhau).

> Nếu bạn đổi `MINIO_ROOT_PASSWORD`, `POSTGRES_PASSWORD` hoặc `ORACLE_APP_USER_PASSWORD`, phải sửa thêm các file sau cho khớp (các file này không tự đọc `.env`):
> - `infrastructure/trino/etc/catalog/iceberg.properties`
> - `infrastructure/trino/etc/catalog/postgresql.properties`
> - `infrastructure/trino/etc/catalog/oracle.properties`
> - `infrastructure/spark/conf/spark-defaults.conf`

> **Riêng `SUPERSET_DB_PASSWORD` — không được chứa ký tự `@ : / ? #`...** Password này bị nhúng vào connection string nội bộ của Superset; Superset/Alembic tự ghép lại chuỗi này ở nhiều điểm mà không có cách override từ bên ngoài, nên ký tự URL-reserved sẽ làm vỡ kết nối tới Postgres (chi tiết xem [docs/huong-dan-chay-ha-tang.md](docs/huong-dan-chay-ha-tang.md) mục 2). `AIRFLOW_DB_PASSWORD` không bị giới hạn này (đã tự xử lý qua script `render_db_conn.py`).

## 3. Chạy hạ tầng

```bash
docker compose up -d
```

Lần đầu chạy sẽ tải image, có thể mất 10–20 phút tuỳ mạng. Kiểm tra trạng thái:

```bash
docker compose ps
```

Hướng dẫn chi tiết từng bước, cách xem log, cách dừng/xoá, và các lỗi thường gặp: xem [docs/huong-dan-chay-ha-tang.md](docs/huong-dan-chay-ha-tang.md).

## 4. Truy cập nhanh các service

| Service | URL |
|---|---|
| MinIO Console | http://localhost:9001 |
| Spark Master UI | http://localhost:8080 |
| Trino UI | http://localhost:8082 |
| Airflow Webserver | http://localhost:8083 |
| Superset | http://localhost:8088 |

Port lấy theo giá trị mặc định trong `.env.example` — nếu bạn đổi port trong `.env`, dùng port mới tương ứng. Tài khoản đăng nhập từng service xem trong `.env` (các biến `*_ADMIN_USER` / `*_ADMIN_PASSWORD`, `*_ROOT_USER` / `*_ROOT_PASSWORD`).

## 5. Cấu trúc thư mục

```
project-de/
├── .env.example          # Mẫu file cấu hình, copy thành .env rồi điền giá trị thật
├── docker-compose.yml    # Khai báo toàn bộ service hạ tầng
├── docs/                 # Tài liệu chi tiết
│   ├── docker-compose-guide.md     # Giải thích ý nghĩa từng field trong docker-compose.yml
│   └── huong-dan-chay-ha-tang.md   # Hướng dẫn chạy, truy cập, troubleshooting
├── infrastructure/       # Config, Dockerfile & init script cho từng service
│   ├── airflow/{Dockerfile,config,logs,plugins}/   # Dockerfile: build thêm JDK + pin pyspark
│   ├── oracle/init/
│   ├── postgres/init/
│   ├── spark/{Dockerfile,conf}/       # Dockerfile: build thêm Python 3.12 (khớp driver Airflow)
│   ├── superset/{Dockerfile,superset_config.py}/  # Dockerfile: build thêm driver Trino
│   └── trino/etc/catalog/
└── tests/                # DAG + job Spark dùng để test connectivity (mount vào container Airflow)
    ├── dags/
    └── jobs/
```

## 6. Tài liệu chi tiết

- [docs/docker-compose-guide.md](docs/docker-compose-guide.md) — ý nghĩa các trường cấu hình (`environment`, `depends_on`, `healthcheck`...) và vai trò từng service trong `docker-compose.yml`.
- [docs/huong-dan-chay-ha-tang.md](docs/huong-dan-chay-ha-tang.md) — hướng dẫn chạy từng bước, bảng truy cập đầy đủ, cách dừng/xoá, lỗi thường gặp.
