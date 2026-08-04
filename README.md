# TaskHub API

TaskHub la API quan ly workspace, project, task, label va comment bang FastAPI, PostgreSQL va Redis trong Docker Compose.

## Chay Du An

```powershell
docker compose up --build
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

## Docs

- [RBAC policy](docs/RBAC.md)
- [API error format va request id](docs/API_ERRORS.md)
- [Logging, Docker logs va seed demo](docs/LOGGING.md)

## Kiem Tra

```powershell
docker compose exec app pytest -q
docker compose exec app ruff check app tests
docker compose exec app mypy app tests
```
