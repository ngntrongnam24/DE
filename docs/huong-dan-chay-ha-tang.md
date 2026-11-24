# Hướng dẫn chạy hạ tầng lakehouse

## 1. Yêu cầu trước khi chạy

- Máy đã cài **Docker Desktop** (Windows, có bật WSL2 backend) và **Docker Compose** (đi kèm sẵn trong Docker Desktop, không cần cài riêng).
- RAM trống tối thiểu khoảng **8GB** (Oracle XE + Spark + Trino + Airflow + Superset cùng chạy khá nặng).
- Đã mở Docker Desktop và Docker đang chạy (icon Docker ở system tray không bị đỏ/lỗi).

Kiểm tra Docker đã sẵn sàng:

```bash
docker --version
docker compose version
```

Nếu 2 lệnh trên chạy ra số version, tức là đã dùng được.

## 2. Các file cấu hình trong `infrastructure/`

Toàn bộ file cấu hình cần thiết đã có đủ trong `infrastructure/`:

| File | Dùng cho service nào | Vai trò |
|---|---|---|
| `infrastructure/postgres/init/01-init-databases.sh` | `postgres` | Tạo 3 database (`airflow`, `superset`, `iceberg_catalog`) và user tương ứng. |
| `infrastructure/airflow/config/render_db_conn.py` | `airflow-init`, `airflow-webserver`, `airflow-scheduler` | Tự build connection string tới Postgres có URL-encode user/password (xem lưu ý bên dưới). |
| `infrastructure/trino/etc/node.properties` | `trino` | Cấu hình node Trino. |
| `infrastructure/trino/etc/jvm.config` | `trino` | Cấu hình JVM cho Trino. |
| `infrastructure/trino/etc/config.properties` | `trino` | Cấu hình coordinator/port của Trino. |
| `infrastructure/trino/etc/catalog/iceberg.properties` | `trino` | Catalog Iceberg — nối tới `iceberg-rest` + MinIO. |
| `infrastructure/trino/etc/catalog/postgresql.properties` | `trino` | Catalog Postgres — cho phép Trino query thẳng DB `postgres`. |
| `infrastructure/trino/etc/catalog/oracle.properties` | `trino` | Catalog Oracle — cho phép Trino query thẳng Oracle XE. |
| `infrastructure/spark/conf/spark-defaults.conf` | `spark-master`, `spark-worker` | Khai báo package Iceberg/S3 và thông tin catalog cho Spark. |
| `infrastructure/spark/Dockerfile` | `spark-master`, `spark-worker` | Build thêm Python 3.12 (từ source) vào image `apache/spark:3.5.5` — khớp version với driver Airflow, tránh lỗi `PYTHON_VERSION_MISMATCH`. |
| `infrastructure/airflow/Dockerfile` | `airflow-init`, `airflow-webserver`, `airflow-scheduler` | Build thêm JDK 17 + pin version `pyspark`/`apache-airflow-providers-apache-spark` vào image `apache/airflow:2.9.3`, cần để `spark-submit` chạy được từ container Airflow. |
| `infrastructure/superset/superset_config.py` | `superset-init`, `superset` | File config Superset, trỏ qua biến `SUPERSET_CONFIG_PATH`. |
| `infrastructure/superset/Dockerfile` | `superset-init`, `superset` | Build thêm driver `trino`/`sqlalchemy-trino` vào image `apache/superset:3.1.0` (image gốc không có sẵn). |

> Lưu ý: các file catalog của Trino và `spark-defaults.conf` có **hardcode sẵn** user/password (hiện khớp với `minioadmin`/`postgres`/`lakehouse` + password tương ứng trong `.env`). Nếu bạn đổi user/password trong `.env`, phải sửa thủ công lại đúng các file này (các file properties này không tự đọc `.env`).

> **Lưu ý quan trọng về password chứa ký tự đặc biệt**: `AIRFLOW_DB_PASSWORD` và `SUPERSET_DB_PASSWORD` bị nhúng vào một connection string dạng `user:password@host` ở bên trong Airflow/Superset. Nếu password chứa ký tự URL-reserved (`@ : / ? # ...`), connection string sẽ bị parse sai và service lỗi kết nối DB (lỗi thật đã gặp khi dùng password `aA@123456`):
> - **Airflow**: đã xử lý bằng script `render_db_conn.py` tự URL-encode password — password `AIRFLOW_DB_PASSWORD` chứa `@` vẫn dùng được bình thường.
> - **Superset**: không xử lý được bằng config override (Superset/Alembic tự ghép lại connection string ở nhiều điểm nội bộ) — `SUPERSET_DB_PASSWORD` **bắt buộc không được chứa** các ký tự URL-reserved.
> - Các password khác (`MINIO_ROOT_PASSWORD`, `POSTGRES_PASSWORD`, `ORACLE_APP_USER_PASSWORD`, `ICEBERG_CATALOG_DB_PASSWORD`, `*_ADMIN_PASSWORD`) không bị giới hạn này vì không bị nhúng vào URI — dùng ký tự gì cũng được.

> Lưu ý về MinIO: image `minio/minio`/`minio/mc` chính thức trên Docker Hub đã bị MinIO Inc. khoá pull công khai (giữa 2025). Service `minio` trong `docker-compose.yml` hiện dùng `bitnamilegacy/minio` — image này **tự tạo bucket `warehouse` lúc khởi động** (qua biến `MINIO_DEFAULT_BUCKETS`) nên không còn service `mc` riêng như thiết kế ban đầu. Image này cũng mặc định **tắt web console** (`MINIO_BROWSER=off`) nên đã set thêm `MINIO_BROWSER: "on"` trong `docker-compose.yml` để console port 9001 hoạt động.

> Lưu ý về Spark: ban đầu cũng dùng `bitnamilegacy/spark:3.5.5-debian-12-r6` cùng lý do trên, nhưng đã đổi sang image **chính thức** `apache/spark:3.5.5` (Apache Software Foundation publish, không bị giới hạn pull) — build thêm qua `infrastructure/spark/Dockerfile` thành `lakehouse-spark:3.5.5` để cài Python 3.12 (image gốc chỉ có Python 3.8, trong khi driver Spark chạy từ container Airflow dùng Python 3.12 — PySpark bắt buộc khớp minor version, nếu không sẽ lỗi `PYTHON_VERSION_MISMATCH`). Chi tiết xem [docker-compose-guide.md mục 2.5](docker-compose-guide.md#25-spark-master--spark-worker).

> Lưu ý về Superset: image gốc `apache/superset:3.1.0` không có driver kết nối Trino — đã build thêm qua `infrastructure/superset/Dockerfile` (cài `trino` + `sqlalchemy-trino`) thành `lakehouse-superset:3.1.0`. Nếu tạo database connection Trino trong Superset UI mà báo lỗi `Could not load database driver: TrinoEngineSpec`, kiểm tra lại service `superset`/`superset-init` có đang chạy đúng image `lakehouse-superset:3.1.0` không (`docker compose ps`).

## 3. Các bước chạy hạ tầng

### Bước 1 — Vào đúng thư mục project

```bash
cd "d:\Learning\Học\DE\slide TPBank\project-de"
```

### Bước 2 — Kiểm tra file `.env`

File `.env` ở root chứa toàn bộ user/password/port/image version. Dùng được ngay với giá trị mặc định để test. Nếu muốn đổi password/port, sửa trực tiếp trong `.env`, không cần sửa `docker-compose.yml`.

### Bước 3 — Khởi động toàn bộ hạ tầng

```bash
docker compose up -d
```

- `-d`: chạy ngầm (detached), không chiếm terminal.
- Lần đầu chạy sẽ **tải image** (Oracle, Spark, Trino, Airflow, Superset... khá nặng) — có thể mất 10–20 phút tuỳ mạng.
- Docker Compose tự chạy theo đúng thứ tự phụ thuộc (`postgres` → `airflow-init`/`superset-init` → các service còn lại), không cần chạy tay từng service.

### Bước 4 — Theo dõi quá trình khởi động

Xem trạng thái tất cả container:

```bash
docker compose ps
```

Cột `STATUS` cần đạt `running` (hoặc `healthy` với service có healthcheck). Các container dạng "init" (`airflow-init`, `superset-init`) chạy xong sẽ tự **Exited (0)** — đây là bình thường, không phải lỗi.

Xem log của một service cụ thể (khi cần debug):

```bash
docker compose logs -f <tên-service>
```

Ví dụ: `docker compose logs -f airflow-webserver`

Nhấn `Ctrl + C` để thoát xem log (không làm container tắt).

### Bước 5 — Chờ các service "init" chạy xong

Thứ tự khởi động thực tế:

1. `postgres` chạy và healthy.
2. `minio` chạy, tự tạo bucket `warehouse` lúc khởi động, rồi healthy.
3. `iceberg-rest` start (cần cả `postgres` và `minio` healthy).
4. `airflow-init` migrate database + tạo user admin → tắt → `airflow-webserver`, `airflow-scheduler` mới start.
5. `superset-init` migrate database + tạo user admin → tắt → `superset` mới start.
6. `spark-master`, `spark-worker`, `trino` start độc lập, không phụ thuộc nhiều.

Toàn bộ quá trình này tự động, chỉ cần đợi khoảng 1–3 phút sau khi gõ lệnh `up -d`.

## 4. Truy cập các service

| Service | URL | Tài khoản mặc định |
|---|---|---|
| MinIO Console | http://localhost:9001 | `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` |
| MinIO API (S3 endpoint) | http://localhost:9000 | — |
| Spark Master UI | http://localhost:8080 | — |
| Spark Worker UI | http://localhost:8081 | — |
| Trino UI | http://localhost:8082 | Username bất kỳ (chưa cấu hình authentication thật, xem mục 6) |
| Airflow Webserver | http://localhost:8083 | `AIRFLOW_ADMIN_USER` / `AIRFLOW_ADMIN_PASSWORD` |
| Superset | http://localhost:8088 | `SUPERSET_ADMIN_USER` / `SUPERSET_ADMIN_PASSWORD` |
| Iceberg REST Catalog | http://localhost:8181 | — (gọi qua API, không có UI) |
| PostgreSQL | `localhost:5432` | `POSTGRES_USER` / `POSTGRES_PASSWORD` |
| Oracle XE | `localhost:1521` | `ORACLE_APP_USER` / `ORACLE_APP_USER_PASSWORD` (hoặc `system` / `ORACLE_PASSWORD`) |

> Giá trị thật của tất cả tên biến trên lấy trong file `.env` — vì đây là password do bạn tự đặt (không phải giá trị cố định như `admin`/`admin`). Port cũng lấy từ `.env`, đổi port ở đó thì dùng port mới khi truy cập.

## 5. Dừng / xoá hạ tầng

Dừng toàn bộ container (giữ lại dữ liệu):

```bash
docker compose stop
```

Chạy lại sau khi đã dừng:

```bash
docker compose start
```

Dừng và **xoá container** (giữ lại volume, tức giữ data):

```bash
docker compose down
```

Dừng và **xoá cả volume** (mất toàn bộ data: database, bucket MinIO...) — chỉ dùng khi muốn làm lại từ đầu:

```bash
docker compose down -v
```

## 6. Một số lỗi thường gặp

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `airflow-init`/`superset-init` ở trạng thái `Exited (1)` | Service phụ thuộc (`postgres`) chưa healthy, hoặc nội dung file script ở mục 2 bị sửa sai | Xem log: `docker compose logs <tên-service>` để biết lỗi cụ thể |
| `minio` không lên healthy, log báo lỗi pull image | Image `bitnamilegacy/minio` bị đổi tag/không còn tồn tại | Kiểm tra lại giá trị `MINIO_IMAGE` trong `.env` |
| `airflow-webserver` khởi động nhưng không healthy | `airflow-init` chưa chạy xong hoặc chạy lỗi | `docker compose logs airflow-init` để xem lỗi migrate DB |
| Trino container tắt ngay sau khi start | Nội dung `node.properties`/`jvm.config`/`config.properties` bị sửa sai cú pháp | Xem log `docker compose logs trino`, so lại với nội dung gốc trong mục 2 |
| Port bị trùng, container không start được | Port đó đã có chương trình khác trên máy dùng (ví dụ cổng 5432 đã có Postgres local khác chạy) | Đổi port tương ứng trong `.env`, chạy lại `docker compose up -d` |
| Máy chậm/treo khi chạy `up -d` | Không đủ RAM cho toàn bộ service cùng lúc | Tăng RAM cấp cho Docker Desktop (Settings → Resources), hoặc tắt bớt service không cần test (dùng `docker compose up -d <tên-service>` để chạy từng phần) |
| `airflow-init`/`superset-init` lỗi `could not translate host name "...@postgres"` | `AIRFLOW_DB_PASSWORD`/`SUPERSET_DB_PASSWORD` chứa ký tự URL-reserved (`@`...) làm vỡ connection string | Với Airflow: đã tự xử lý qua `render_db_conn.py`, kiểm tra lại script này còn nguyên vẹn. Với Superset: đổi `SUPERSET_DB_PASSWORD` sang không chứa ký tự đặc biệt, rồi `docker compose down -v` + `up -d` lại (phải xoá volume vì role Postgres cũ đã tạo với password cũ) |
| `superset-init` lỗi `relation "tables" does not exist` dù đã đổi password | Database `superset` còn ở trạng thái dở từ lần chạy lỗi trước (alembic đánh dấu đã migrate nhưng bảng chưa tạo đủ) | `docker compose down -v` để xoá sạch volume Postgres rồi `up -d` lại từ đầu |
| MinIO console (`:9001`) trả "Empty reply from server" | Image Bitnami mặc định `MINIO_BROWSER=off` | Đã set `MINIO_BROWSER: "on"` trong `docker-compose.yml`, kiểm tra biến này còn tồn tại trong service `minio` |
| Job Spark fail với `pyspark.errors.exceptions.base.PySparkRuntimeError: [PYTHON_VERSION_MISMATCH]` | Python của driver (container Airflow) và executor (`spark-worker`) lệch minor version | Đảm bảo `spark-worker`/`spark-master` đang chạy image `lakehouse-spark:3.5.5` (có Python 3.12, build từ `infrastructure/spark/Dockerfile`) **và** job/DAG có set `spark.pyspark.python=/usr/local/bin/python3.12` trong `conf` — chỉ build Python vào image không đủ, phải khai báo đúng conf key này (không phải `spark.executorEnv.PYSPARK_PYTHON`, key đó không có tác dụng) |
| Superset báo `Could not load database driver: TrinoEngineSpec` khi tạo kết nối Trino | Service `superset`/`superset-init` đang chạy image gốc `apache/superset` thay vì `lakehouse-superset:3.1.0` | `docker compose build superset-init superset && docker compose up -d --force-recreate superset-init superset` |
| Sửa `Dockerfile` (`spark`/`airflow`/`superset`) nhưng `docker compose up -d` không áp dụng thay đổi | Compose chỉ tự build khi image chưa tồn tại, không tự rebuild khi Dockerfile đổi nhưng tag image giữ nguyên | Chạy `docker compose build <tên-service>` rồi `docker compose up -d --force-recreate <tên-service>` |

## 7. Chạy riêng một phần (không cần bật toàn bộ)

Nếu chỉ cần test một nhóm service, có thể chỉ định tên:

```bash
docker compose up -d postgres minio
```

Compose sẽ tự bật kèm các service mà nhóm này phụ thuộc.
