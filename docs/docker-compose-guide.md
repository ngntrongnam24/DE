# Hướng dẫn cấu hình `docker-compose.yml`

File này giải thích ý nghĩa các trường (field) được dùng trong `docker-compose.yml` ở root project, và cách từng service trong hạ tầng lakehouse được khai báo.

## 1. Ý nghĩa các trường cấu hình chung

### 1.1. Các khối top-level

| Khối | Ý nghĩa |
|---|---|
| `networks` | Khai báo (các) mạng ảo mà container sẽ tham gia. Container cùng network gọi được nhau qua **tên service** (DNS nội bộ của Docker), ví dụ `http://minio:9000`. |
| `volumes` | Khai báo các **named volume** — vùng lưu trữ do Docker quản lý, tồn tại độc lập với vòng đời container. Dùng cho dữ liệu cần giữ lại khi container bị xoá/tạo lại (data của Oracle, MinIO, Postgres...). |
| `services` | Danh sách các container sẽ được tạo. Mỗi key con (`oracle-db`, `minio`, `postgres`, ...) là một service/container riêng. |

### 1.2. Các trường trong mỗi service

| Trường | Ý nghĩa |
|---|---|
| `image` | Image Docker sẽ dùng để tạo container, dạng `<repo>:<tag>`. Ở đây đều được tham số hoá qua biến `.env` (ví dụ `${ORACLE_IMAGE}`) để dễ đổi version mà không sửa compose file. |
| `container_name` | Tên cố định đặt cho container (thay vì tên tự sinh của Docker), giúp dễ gọi `docker logs <tên>`, `docker exec <tên>`. |
| `restart` | Chính sách tự khởi động lại container. `unless-stopped`: tự restart khi container bị crash hoặc Docker daemon khởi động lại, **trừ khi** người dùng chủ động `docker stop`. Không đặt ở các service "init" (chạy 1 lần rồi tắt) vì không cần restart. |
| `command` | Override lệnh mặc định (`CMD`) của image. Dùng khi image là generic và cần chỉ định rõ nó chạy ở mode nào (ví dụ MinIO cần biết chạy `server /data`). |
| `entrypoint` | Override `ENTRYPOINT` của image — lệnh gốc sẽ thực thi khi container start. Dùng kết hợp với `command` khi cần chạy một script/chuỗi lệnh tuỳ biến (ví dụ các bước init của Airflow, Superset). |
| `environment` | Biến môi trường truyền vào trong container, dùng để cấu hình hành vi của ứng dụng (user/password, connection string, mode chạy...). Giá trị `${...}` được compose thay thế bằng giá trị tương ứng trong file `.env`. |
| `ports` | Mapping cổng dạng `"<cổng trên máy host>:<cổng trong container>"`. Chỉ cổng bên trái là có thể đổi tự do (qua `.env`); cổng bên phải là cổng mà ứng dụng lắng nghe trong container, cố định theo image. |
| `volumes` | Mount dữ liệu vào container, hai dạng dùng trong file này: <br>• **Named volume**: `oracle_data:/opt/oracle/oradata` — Docker tự quản lý, không map ra thư mục cụ thể trên host. <br>• **Bind mount**: `./infrastructure/spark/conf:/opt/bitnami/spark/conf` — map trực tiếp thư mục trên host vào container, dùng để nạp file config/script mình tự viết. |
| `depends_on` | Khai báo thứ tự khởi động giữa các service. Có 2 dạng điều kiện (`condition`) dùng trong file này: <br>• `service_healthy`: chờ service phụ thuộc có healthcheck trả "healthy" rồi mới start (không chỉ chờ container "running"). <br>• `service_completed_successfully`: chờ service phụ thuộc (dạng job chạy-một-lần) **thoát với exit code 0** rồi mới start — dùng cho các bước init (`airflow-init`, `superset-init`). |
| `healthcheck` | Lệnh Docker tự chạy định kỳ bên trong container để xác định service đã "sẵn sàng" hay chưa (không chỉ là "process đang chạy"). Gồm: <br>• `test`: lệnh kiểm tra, exit code 0 = healthy. <br>• `interval`: khoảng cách giữa 2 lần check. <br>• `timeout`: thời gian tối đa chờ 1 lần check. <br>• `retries`: số lần fail liên tiếp tối đa trước khi coi là "unhealthy". <br>• `start_period`: thời gian "ân hạn" sau khi container start, fail trong giai đoạn này chưa tính vào `retries` (dành cho service khởi động chậm). |
| `networks` (trong service) | Service tham gia network nào trong số các network đã khai báo ở top-level. Tất cả service ở đây đều dùng chung `lakehouse_net` để có thể gọi nhau qua tên service. |
| `user` | Chỉ định UID:GID chạy process trong container, thay vì dùng user mặc định của image. Dùng cho Airflow (`${AIRFLOW_UID}:0`) để file ghi ra (`dags/`, `logs/`...) có quyền sở hữu khớp với user trên host, tránh lỗi permission. |
| `&anchor` / `*anchor` (YAML anchor/alias) | Cú pháp YAML thuần (không riêng của Compose): `&airflow-common-env` đặt tên cho một block, `*airflow-common-env` tái sử dụng lại chính block đó ở service khác — tránh phải lặp lại cùng một đoạn `environment` ở nhiều service (3 service Airflow, 2 service Superset). |

Toàn bộ giá trị `${TÊN_BIẾN}` trong compose file được Docker Compose đọc từ file `.env` cùng cấp — đây là nơi duy nhất cần sửa image tag, port, username/password mà không cần đụng vào `docker-compose.yml`.

## 2. Các service trong hạ tầng

### 2.1. `oracle-db`
Database Oracle XE — đóng vai trò hệ nguồn OLTP mẫu để các pipeline ingest (Spark/Airflow) đọc dữ liệu đưa vào lakehouse.
- `healthcheck` dùng chính script `healthcheck.sh` có sẵn trong image `gvenzl/oracle-xe`.
- Thư mục `./infrastructure/oracle/init` được mount vào `/container-entrypoint-initdb.d` — các script `.sql`/`.sh` đặt ở đây sẽ tự chạy khi container khởi tạo lần đầu (tạo schema/bảng mẫu).
- Volume `oracle_data` giữ lại datafile của Oracle qua các lần restart container.

### 2.2. `minio`
Object storage tương thích S3, đóng vai trò **warehouse layer** vật lý cho Iceberg (nơi lưu data file + metadata file thực tế). Dùng image `bitnamilegacy/minio` (image gốc `minio/minio`/`minio/mc` trên Docker Hub đã bị MinIO Inc. khoá pull công khai).
- Không cần khai báo `command` — entrypoint của image Bitnami tự chạy MinIO server với cổng mặc định 9000 (API) và 9001 (console).
- `MINIO_DEFAULT_BUCKETS: ${MINIO_BUCKET}`: image tự tạo sẵn bucket này lúc khởi động (dùng `mc` được bundle sẵn trong image), **không cần container `mc` riêng** như thiết kế ban đầu.
- `MINIO_BROWSER: "on"`: image Bitnami **mặc định tắt web console** (`MINIO_BROWSER=off`, khác hành vi image gốc) — không set biến này thì cổng 9001 vẫn mở nhưng trả về rỗng (empty reply), không có UI.
- `healthcheck` dùng `mc ready local` — `mc` có sẵn trong image Bitnami, hiểu alias đặc biệt `local` để tự kiểm tra chính MinIO đang chạy trong cùng container.
- Volume mount vào `/bitnami/minio/data` (đường dẫn data mặc định của image Bitnami, khác với image gốc dùng `/data`).

> Lưu ý lịch sử: thiết kế ban đầu có 1 service `mc` riêng chạy script `create-buckets.sh` để tạo bucket, dùng image `minio/minio` + `minio/mc` chính thức. Giữa năm 2025, MinIO Inc. khoá quyền pull công khai với cả 2 image này (Docker Hub, quay.io, và cả file binary tải trực tiếp đều bị chặn) — đã đổi sang `bitnamilegacy/minio` (image Bitnami lưu các version cũ, maintain bởi Broadcom) và bỏ hẳn service `mc` vì image mới tự tạo bucket được.

### 2.3. `postgres`
Database quan hệ dùng làm **metadata store chung** cho 3 thành phần: metadata DB của Airflow, metadata DB của Superset, và backend JDBC của Iceberg REST Catalog — mỗi thành phần có DB/user riêng (biến `AIRFLOW_DB*`, `SUPERSET_DB*`, `ICEBERG_CATALOG_DB*`), tạo bởi script init trong `./infrastructure/postgres/init`.
- `healthcheck` dùng `pg_isready`, các service phụ thuộc Postgres đều chờ `service_healthy`.

### 2.4. `iceberg-rest`
Iceberg REST Catalog — service trung gian quản lý **metadata của table Iceberg** (schema, snapshot, partition...), được Spark và Trino cùng gọi tới để biết cấu trúc/đọc-viết table.
- `CATALOG_CATALOG__IMPL=...JdbcCatalog`: chọn backend lưu catalog là JDBC (ghi vào Postgres) thay vì lưu trong memory.
- `CATALOG_URI`: connection string tới DB `iceberg_catalog` trên Postgres.
- `CATALOG_WAREHOUSE`: đường dẫn S3 gốc (`s3://warehouse/`) nơi data file thực tế được ghi — chính là bucket được MinIO tự tạo lúc khởi động (`MINIO_DEFAULT_BUCKETS`).
- `CATALOG_IO__IMPL` + các biến `AWS_*`, `CATALOG_S3_*`: cấu hình để Iceberg biết cách kết nối tới MinIO như một S3 endpoint (MinIO tương thích S3 API nên dùng chung S3FileIO của Iceberg).
- Phải chờ cả `postgres` (có DB để lưu catalog) và `minio` (bucket đã tồn tại) healthy.

### 2.5. `spark-master` / `spark-worker`
Cluster Spark ở mode tối giản (1 master + 1 worker), dùng để chạy job đọc/transform/viết dữ liệu vào table Iceberg qua REST catalog ở trên. Dùng image **chính thức** `apache/spark:3.5.5` (Apache Software Foundation publish, không bị khoá pull như Bitnami/MinIO), build thêm qua `infrastructure/spark/Dockerfile` thành image `lakehouse-spark:3.5.5`.
- Không dùng `SPARK_MODE` như Bitnami — image chính thức không có entrypoint tự detect master/worker, nên `command:` gọi thẳng `spark-class org.apache.spark.deploy.master.Master` (hoặc `...worker.Worker`) kèm các flag `--host/--port/--webui-port` (master) hay `--cores/--memory/--webui-port` (worker, lấy giá trị từ `SPARK_WORKER_CORES`/`SPARK_WORKER_MEMORY` qua compose interpolation `${...}`), và địa chỉ master `spark://spark-master:7077` được truyền thẳng làm tham số cuối của `spark-worker`.
- Cả hai cùng mount `./infrastructure/spark/conf` vào `/opt/spark/conf` (path của image chính thức, khác `/opt/bitnami/spark/conf` của Bitnami trước đây) — nơi đặt `spark-defaults.conf` khai báo package Iceberg/S3 và thông tin catalog.
- **`infrastructure/spark/Dockerfile`**: image gốc `apache/spark:3.5.5` chạy Ubuntu 20.04 kèm Python 3.8 mặc định, trong khi driver Spark (chạy từ container Airflow, deploy-mode `client`) dùng Python 3.12 — PySpark bắt buộc driver/executor phải khớp **minor version** Python, nếu không sẽ lỗi `PYTHON_VERSION_MISMATCH`. Dockerfile này build thêm Python 3.12 từ source (tải trực tiếp từ python.org, không dùng PPA deadsnakes vì từng gặp PPA resolve nhầm gói không liên quan trên Ubuntu 20.04) và cài vào `/usr/local/bin/python3.12`.
- Chỉ build Python vào image là **chưa đủ** — phải khai báo thêm Spark conf `spark.pyspark.python=/usr/local/bin/python3.12` ở phía job submit (xem `tests/dags/*.py`, dùng tham số `conf` của `SparkSubmitOperator`) để driver chỉ định đúng executable này cho executor dùng. PySpark **không tự đọc** biến môi trường `PYSPARK_PYTHON`/`spark.executorEnv.PYSPARK_PYTHON` đặt sẵn trong image executor — giá trị thực sự được dùng đến từ Spark conf `spark.pyspark.python` do driver truyền xuống lúc submit job.

### 2.6. `trino`
Query engine SQL, đóng vai trò lớp **truy vấn** phục vụ Superset (và người dùng trực tiếp), có thể query thẳng table Iceberg (qua `iceberg-rest`) cũng như federation sang Postgres/Oracle.
- Không có biến `environment` vì toàn bộ cấu hình của Trino (catalog, JVM, node) được định nghĩa bằng **file**, mount trực tiếp từ `./infrastructure/trino/etc` vào `/etc/trino` (thay thế cấu hình mặc định của image).
- `depends_on.iceberg-rest.condition: service_started`: chỉ cần container đã start (REST catalog không có healthcheck riêng) là Trino có thể start theo — việc catalog có sẵn sàng thật hay chưa do Trino tự retry khi connector `iceberg` được dùng.

### 2.7. `airflow-init` / `airflow-webserver` / `airflow-scheduler`
Ba container cùng dùng 1 image Airflow (build qua `infrastructure/airflow/Dockerfile` thành `lakehouse-airflow:2.9.3`) nhưng đóng 3 vai trò khác nhau trong một cụm Airflow chạy `LocalExecutor`:
- **`infrastructure/airflow/Dockerfile`**: image gốc `apache/airflow:2.9.3` không có JVM — cần JVM để `spark-submit`/PySpark chạy được từ bên trong container Airflow (dùng `SparkSubmitOperator` với `deploy_mode=client`, tức tiến trình driver Spark chạy ngay trong container Airflow chứ không phải trên `spark-master`). Dockerfile cài thêm `openjdk-17-jre-headless` và pin `apache-airflow-providers-apache-spark`, `pyspark` (khớp version `3.5.5` với `spark-master`/`spark-worker` — xem mục 2.5).
- **`airflow-init`**: job chạy một lần — `airflow db migrate` (tạo schema trong Postgres) rồi `airflow users create` (tạo user admin). Không có `restart`, không expose port, chỉ chạy xong rồi thoát.
- **`airflow-webserver`**: chạy UI quản trị Airflow, expose cổng `${AIRFLOW_WEBSERVER_PORT}` ra ngoài; có `healthcheck` gọi endpoint `/health`.
- **`airflow-scheduler`**: tiến trình lập lịch, quét `dags/` và kích hoạt task — không cần expose port vì không có giao diện riêng.
- `AIRFLOW__CORE__EXECUTOR=LocalExecutor`: chạy task trực tiếp trên máy chạy scheduler (không cần Celery/Redis) — phù hợp quy mô dev/demo.
- `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN_CMD: python3 /opt/airflow/config/render_db_conn.py`: thay vì ghép thẳng connection string trong YAML (`...@${AIRFLOW_DB_PASSWORD}@postgres...`), dùng cơ chế `_CMD` của Airflow để gọi script Python tự `urllib.parse.quote_plus` user/password trước khi build URI. Lý do: nếu `AIRFLOW_DB_PASSWORD` chứa ký tự URL-reserved (`@`, `:`...), ghép thẳng trong YAML sẽ làm vỡ connection string (lỗi thật đã gặp: `could not translate host name "...@postgres"`). Script đọc 3 biến `AIRFLOW_DB_USER`/`AIRFLOW_DB_PASSWORD`/`AIRFLOW_DB` được khai báo thêm trong cùng khối `environment` để dùng `os.environ`. Đây là nơi Airflow lưu toàn bộ metadata (DAG run, task instance, connection, variable...).
- Khối `environment: &airflow-common-env` ở `airflow-init` được định nghĩa một lần và tái sử dụng (`*airflow-common-env`) ở hai service còn lại để đảm bảo cả 3 luôn trỏ về cùng một DB.
- Cả 3 cùng mount `dags/`, `logs/`, `plugins/`, `config/` từ `./infrastructure/airflow/` — DAG viết ra ở đây sẽ được cả scheduler và webserver thấy.
- `airflow-webserver`/`airflow-scheduler` đều `depends_on.airflow-init.condition: service_completed_successfully` — phải migrate DB xong mới được start, tránh lỗi "chưa có schema".

### 2.8. `superset-init` / `superset`
Hai container cùng image Superset (build qua `infrastructure/superset/Dockerfile` thành `lakehouse-superset:3.1.0`), mô hình init-job + service tương tự Airflow:
- **`infrastructure/superset/Dockerfile`**: image gốc `apache/superset:3.1.0` **không có sẵn driver kết nối Trino** (chỉ có `PyHive`, một driver khác không tương thích) — nếu dùng thẳng image gốc, tạo database connection kiểu Trino trong Superset UI sẽ báo lỗi `Could not load database driver: TrinoEngineSpec`. Dockerfile cài thêm `pip install trino sqlalchemy-trino` để đăng ký đúng dialect SQLAlchemy cho Trino.
- **`superset-init`**: chạy `superset db upgrade` (tạo/migrate schema metadata của Superset trong Postgres), `superset fab create-admin` (tạo user admin), `superset init` (tạo role/permission mặc định). Chạy xong thì thoát.
- **`superset`**: service chạy thật, expose UI qua cổng `${SUPERSET_PORT}` (8088), chỉ start sau khi `superset-init` hoàn tất thành công.
- `DATABASE_*`: các biến mà image Superset dùng để tự sinh connection string tới Postgres (DB `superset`) cho metadata của chính Superset — khác với các connection mà người dùng sẽ khai báo trong UI để Superset query dữ liệu qua Trino.
- **Quan trọng**: `SUPERSET_DB_PASSWORD` (giá trị gán cho `DATABASE_PASSWORD`) **không được chứa ký tự URL-reserved** (`@ : / ? #`...). Khác với Airflow, lỗi này không vá được bằng cách custom `superset_config.py` — Alembic (công cụ migrate của Superset) tự ghép lại connection string ở bước `db upgrade` theo cách riêng, không đi qua config override của mình, nên vẫn vỡ URI dù đã override đúng ở file config. Giải pháp triệt để là chọn password không có ký tự đặc biệt cho riêng biến này.
- `SUPERSET_CONFIG_PATH`: chỉ định file `superset_config.py` (mount qua `./infrastructure/superset`) chứa các override cấu hình nâng cao (secret key, feature flag...).
- Cả hai cùng dùng named volume `superset_home` để giữ lại các dữ liệu runtime Superset tự sinh ra (cache, asset...).

## 3. Thứ tự khởi động tổng quát

```
postgres ──┬─► airflow-init ──► airflow-webserver / airflow-scheduler
           ├─► superset-init ──► superset
           └─► iceberg-rest ◄── minio (tự tạo bucket lúc start)
                    ▲
         spark-master/worker, trino (phụ thuộc iceberg-rest đã start)
```

Toàn bộ thứ tự này được Compose tự suy ra từ `depends_on` khi chạy `docker compose up -d` — không cần chạy từng service theo tay.
