# Delivery Checklist

Tai lieu nay tong hop cac muc can kiem tra truoc khi ban giao TaskHub.

## Tinh Nang Da Co

- Docker Compose chay app, PostgreSQL va Redis.
- Health endpoint kiem tra DB/Redis.
- SQLAlchemy async va Alembic migration.
- User module va pagination schema.
- Auth JWT:
  - register.
  - login.
  - refresh.
  - logout revoke refresh token bang Redis.
  - change password.
- Workspace va workspace member.
- Project CRUD va archive.
- Task CRUD, assign, status, priority, due date.
- Label CRUD va attach/detach task label.
- Comment create/list/delete voi ownership rule.
- Task filtering va pagination.
- RBAC helper va permission tests.
- Redis cache task list va invalidation.
- Background notification khi assign task.
- Request ID middleware.
- Access log middleware.
- Unified API error response.
- Swagger/ReDoc metadata va error response docs.
- Seed demo script.
- Integration tests.

## Setup Tu Dau

```powershell
copy .env.example .env
docker compose up --build -d
docker compose exec app alembic upgrade head
curl.exe -i http://localhost:8000/api/v1/health
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

## Quality Gate

```powershell
docker compose exec app pytest -q
docker compose exec app ruff check app tests
docker compose exec app mypy app tests
docker compose exec app alembic current
```

## Endpoint Docs

```text
Swagger: http://localhost:8000/docs
ReDoc:   http://localhost:8000/redoc
Health:  http://localhost:8000/api/v1/health
```

## Docker va Logs

```powershell
docker compose ps
docker compose logs app --tail=100
docker compose exec redis redis-cli keys "taskhub:*"
```

## Known Limitations

- Notification hien tai la dev/log notification, chua gui email SMTP that.
- `ADMIN` da co enum va docs policy, nhung chua co admin API rieng.
- Dockerfile hien toi uu cho dev; production co the can hardening them.
- Test rebuild tu zero bang `docker compose down -v` se xoa volume local, nen chi chay khi da chap nhan mat data dev.

## Final Delivery

Truoc khi commit/tag final:

- `pytest` pass.
- `ruff` pass.
- `mypy` pass.
- Alembic current o head.
- Health endpoint connected DB/Redis.
- README va docs khong lech code.
- `.env` khong nam trong git status.
