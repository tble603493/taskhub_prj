# Logging, Docker Logs va Seed Demo

Tai lieu nay mo ta cach xem log, request id va seed du lieu demo cho TaskHub.

## Access Log

Moi request se co access log dang:

```text
request_id=... method=GET path=/api/v1/health status=200 duration_ms=4.20 client=172.19.0.1
```

Thong tin log gom:

- `request_id`: id request, trung voi response header `X-Request-ID`.
- `method`: HTTP method.
- `path`: API path.
- `status`: HTTP status code.
- `duration_ms`: thoi gian xu ly request.
- `client`: dia chi client trong network Docker.

## Khong Log Du Lieu Nhay Cam

Middleware khong log:

- request body.
- password.
- access token.
- refresh token.
- `Authorization` header.
- `hashed_password`.

Neu can debug auth, chi nen log request id va status code, khong log token.

## Cach Xem Log Docker

Xem 100 dong cuoi:

```powershell
docker compose logs app --tail=100
```

Theo doi log realtime:

```powershell
docker compose logs -f app
```

Goi request test:

```powershell
curl.exe -i http://localhost:8000/api/v1/health
curl.exe -i http://localhost:8000/api/v1/not-found
```

Can thay log tu `app.access`, vi du:

```text
INFO app.access request_id=... method=GET path=/api/v1/health status=200 duration_ms=...
INFO app.access request_id=... method=GET path=/api/v1/not-found status=404 duration_ms=...
```

## Seed Demo

Chay seed demo:

```powershell
docker compose exec app python -m app.scripts.seed_demo
```

Script nay tao du lieu demo:

- 1 workspace.
- owner/editor/viewer demo.
- 1 project active.
- 1 project archived.
- task voi status/priority/assignee khac nhau.
- label.
- comment.

Tai khoan demo:

```text
demo.owner@taskhub.local
demo.editor@taskhub.local
demo.viewer@taskhub.local
password: demo123456
```

Luu y:

- Password tren chi dung cho local/dev demo.
- Khong dung password nay cho production.
- Script co the chay lai nhieu lan va se co gang dung lai data demo da ton tai.

## Swagger Authorize

Mo Swagger:

```text
http://localhost:8000/docs
```

Cach authorize:

1. Chay app bang Docker Compose.
2. Tao user qua `POST /api/v1/auth/register`, hoac chay seed demo.
3. Bam nut `Authorize` tren Swagger.
4. Nhap:
   - `username`: email user, vi du `demo.owner@taskhub.local`.
   - `password`: password, vi du `demo123456`.
5. Swagger se goi `POST /api/v1/auth/login`.
6. Cac endpoint protected se gui Bearer access token tu dong.

Neu authorize bi loi:

- Kiem tra app dang chay o `http://localhost:8000`.
- Kiem tra user da ton tai.
- Kiem tra dung password.
- Kiem tra `tokenUrl` dang la `/api/v1/auth/login`.
