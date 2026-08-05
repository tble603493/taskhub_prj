# TaskHub API

TaskHub la API quan ly workspace, project, task, label va comment bang FastAPI, PostgreSQL va Redis trong Docker Compose.

## Tech Stack

- FastAPI
- SQLAlchemy 2.x async
- Alembic
- PostgreSQL
- Redis
- Pydantic v2
- JWT access/refresh token
- Pytest, Ruff, MyPy
- Docker Compose

## Cau Truc Chinh

```text
app/
  api/             API routers va dependencies
  core/            config, security, logging, exception handling
  db/              database session
  middleware/      request id va access log middleware
  models/          SQLAlchemy models
  repositories/    database query layer
  schemas/         Pydantic schemas
  services/        business logic
  scripts/         local utility scripts
tests/             automated tests
docs/              project documentation
alembic/           database migrations
```

## Yeu Cau

- Docker Desktop
- Git

## Chay Du An

Copy env mau:

```powershell
copy .env.example .env
```

Build va start stack:

```powershell
docker compose up --build
```

Chay migration:

```powershell
docker compose exec app alembic upgrade head
```

Kiem tra health:

```powershell
curl.exe -i http://localhost:8000/api/v1/health
```

Swagger:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

## Database va pgAdmin

Mac dinh Postgres map ra may host:

```text
Host: localhost
Port: 55432
Database: taskhub
Username: taskhub
Password: 12092005
```

Trong container app, database URL phai dung host service `db` va port `5432`:

```text
postgresql+asyncpg://taskhub:12092005@db:5432/taskhub
```

## Seed Demo

```powershell
docker compose exec app python -m app.scripts.seed_demo
```

Tai khoan demo:

```text
demo.owner@taskhub.local
demo.editor@taskhub.local
demo.viewer@taskhub.local
password: demo123456
```

## Migration

Tao migration moi:

```powershell
docker compose exec app alembic revision --autogenerate -m "message"
```

Upgrade database:

```powershell
docker compose exec app alembic upgrade head
```

Xem migration hien tai:

```powershell
docker compose exec app alembic current
```

## Docs

- [RBAC policy](docs/RBAC.md)
- [API error format va request id](docs/API_ERRORS.md)
- [Logging, Docker logs va seed demo](docs/LOGGING.md)
- [Delivery checklist](docs/DELIVERY_CHECKLIST.md)

## Kiem Tra

```powershell
docker compose exec app pytest -q
docker compose exec app ruff check app tests
docker compose exec app mypy app tests
```

## Troubleshooting

Neu app khong ket noi database:

- Kiem tra `DATABASE_URL` trong `.env`.
- Trong container phai dung `db:5432`, khong dung `localhost`.
- Tu may host/pgAdmin dung `localhost:55432`.

Neu Swagger authorize loi:

- Dang ky user truoc bang `POST /api/v1/auth/register`, hoac chay seed demo.
- Bam `Authorize`.
- Nhap email vao field `username`.
- Nhap password vao field `password`.

Neu muon xem cache Redis:

```powershell
docker compose exec redis redis-cli keys "taskhub:*"
```

Neu muon xem log app:

```powershell
docker compose logs app --tail=100
```
