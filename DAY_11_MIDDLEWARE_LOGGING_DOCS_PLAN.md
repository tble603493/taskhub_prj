# Ke Hoach Ngay 11 - Middleware, Exception Handling, Logging, API Docs va Integration Tests

## Muc tieu ngay 11

Dua API TaskHub ve trang thai de van hanh, de debug va de demo. Sau ngay 11, loi API phai tra ve format nhat quan, moi request co request id/log thoi gian xu ly, Swagger/ReDoc ro rang hon, va co integration test chay qua luong chinh cua he thong.

Ket qua mong muon:

- Co format loi thong nhat cho API.
- Co exception handler cho:
  - validation error.
  - HTTP/business error.
  - 404.
  - 500 unexpected error.
- Co middleware request id.
- Co middleware do thoi gian xu ly request.
- Access log co method, path, status code, duration va request id.
- Khong log password, token, refresh token hoac du lieu nhay cam.
- Swagger/ReDoc co tag, summary, description va security Bearer ro hon.
- Co integration test cho flow:
  - register/login.
  - tao workspace.
  - tao project.
  - tao task.
  - tao label.
  - gan label vao task.
  - tao/list/xoa comment.
- Co seed script hoac fixture demo nhanh.

## Trang thai hien tai cua du an

Du an da co:

- FastAPI app:
  - `app/main.py`
  - `app/api/v1/router.py`
- Router theo module:
  - auth.
  - users.
  - workspaces.
  - projects.
  - tasks.
  - labels.
  - comments.
  - health.
- Auth JWT va Bearer token.
- RBAC helper va docs:
  - `app/core/permissions.py`
  - `docs/RBAC.md`
- Redis cache task list va notification khi assign task.
- Tests cho:
  - auth.
  - users.
  - workspaces.
  - projects.
  - tasks.
  - labels.
  - comments.
  - task filters.
  - permissions.
  - cache.
  - notifications.
- Thu muc `app/middleware` da ton tai, nhung chua co middleware that.

Du an chua co:

- Error response schema dung chung.
- Exception handler dang ky trong `main.py`.
- Request ID middleware.
- Access log middleware.
- Cau hinh logging rieng cho app.
- API docs responses dung chung cho cac endpoint.
- Seed script demo nhanh.
- Integration test gom toan bo flow chinh trong mot file.

## Nguyen tac thiet ke ngay 11

- Loi tra ve cho client phai de doc, nhung khong lam lo stack trace.
- Log noi bo co du request id de trace loi.
- Khong log thong tin nhay cam:
  - password.
  - access token.
  - refresh token.
  - Authorization header.
  - hashed password.
- Middleware khong nen nuot loi. Loi nen di qua exception handler.
- Exception handler 500 phai log exception day du cho dev, nhung response cho client chi nen la message chung.
- Error format can on dinh de frontend sau nay dung duoc.
- API docs chi nen bo sung metadata that su co ich, khong viet qua dai.
- Test ngay 11 nen kiem tra behavior, khong phu thuoc text log qua mong manh.

## Format error response de xuat

File de xuat:

```text
app/schemas/error.py
```

Schema nen co:

- `ErrorResponse`
- `ValidationErrorItem`

Format goi y:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Validation failed",
  "details": [
    {
      "field": "body.email",
      "message": "value is not a valid email address"
    }
  ],
  "request_id": "..."
}
```

Muc dich:

- Client nhin vao `code` de xu ly logic.
- User nhin vao `message` de hieu loi.
- Dev dung `request_id` de tim log.
- `details` dung cho validation hoac loi co them ngu canh.

## Ma loi de xuat

- `VALIDATION_ERROR`
  - Request body/query/path sai format.
- `UNAUTHORIZED`
  - Chua login, token sai, token het han.
- `FORBIDDEN`
  - Da login nhung khong du quyen.
- `NOT_FOUND`
  - Resource khong ton tai trong scope.
- `CONFLICT`
  - Trung email, trung project name, trung label name, resource archived.
- `BAD_REQUEST`
  - Input hop le ve format nhung sai business rule.
- `INTERNAL_SERVER_ERROR`
  - Loi ngoai du kien.

## Thu tu lam viec de xuat

### Buoc 1: Kiem tra nen hien tai

Chay:

```powershell
docker compose ps
docker compose exec app pytest -q
docker compose exec app ruff check app tests
docker compose exec app mypy app tests
```

Muc dich:

- Dam bao Ngay 10 sach truoc khi them middleware/handler.
- Neu test cu fail thi sua truoc, tranh nham loi do ngay 11.

## Buoc 2: Tao schema loi dung chung

File:

```text
app/schemas/error.py
```

Noi dung nen co:

- `ErrorResponse`
- `ValidationErrorItem`

Goi y fields `ErrorResponse`:

- `code: str`
- `message: str`
- `details: list[ValidationErrorItem | dict] | None = None`
- `request_id: str | None = None`

Goi y fields `ValidationErrorItem`:

- `field: str`
- `message: str`

Muc dich:

- Swagger hien response loi ro rang.
- Exception handler va docs dung chung schema.
- Frontend sau nay khong phai parse nhieu kieu loi khac nhau.

## Buoc 3: Tao helper lay request id

File de xuat:

```text
app/core/request_context.py
```

Hoac lam don gian trong middleware.

Can co:

- Ten header:

```text
X-Request-ID
```

- Neu client gui `X-Request-ID` thi dung lai.
- Neu client khong gui thi tao `uuid4`.
- Gan request id vao:
  - `request.state.request_id`.
  - response header `X-Request-ID`.

Muc dich:

- Client bao loi co the dua request id.
- Log request va error co cung request id.

## Buoc 4: Tao Request ID middleware

File:

```text
app/middleware/request_id.py
```

Can lam:

- Lay/tai tao request id.
- Gan `request.state.request_id`.
- Them response header `X-Request-ID`.

Muc dich:

- Moi response deu co request id.
- Exception handler co the dua request id vao error response.

Luu y:

- Neu request bi exception, van can co request id trong error response.
- Middleware nay nen duoc add truoc access log middleware hoac dam bao access log doc duoc request id.

## Buoc 5: Tao Access Log middleware

File:

```text
app/middleware/access_log.py
```

Can log:

- request id.
- method.
- path.
- query string neu khong nhay cam.
- status code.
- duration milliseconds.
- client host neu can.

Khong log:

- body request.
- password.
- Authorization header.
- token.

Muc dich:

- Debug nhanh API cham/loi.
- Theo doi request trong Docker logs.

Vi du log dev:

```text
request_id=... method=GET path=/api/v1/tasks status=200 duration_ms=12.4
```

## Buoc 6: Tao cau hinh logging

File de xuat:

```text
app/core/logging.py
```

Can co:

- `configure_logging()`.
- Format log co:
  - timestamp.
  - level.
  - logger name.
  - message.

Muc dich:

- Log cua app nhat quan.
- Sau nay doi sang JSON logging de day len production de hon.

Luu y:

- Ngay 11 chi can logging console don gian.
- Khong can dua structlog/loguru vao neu chua that su can.

## Buoc 7: Tao exception handlers

File de xuat:

```text
app/core/exceptions.py
```

Hoac:

```text
app/api/exception_handlers.py
```

Can co handler cho:

- `RequestValidationError`.
- `HTTPException`.
- `StarletteHTTPException`.
- `Exception`.

Logic:

- Validation error:
  - status `422`.
  - code `VALIDATION_ERROR`.
  - message `Validation failed`.
  - details gom field/message.
- HTTPException:
  - map status code sang code:
    - 400 -> `BAD_REQUEST`.
    - 401 -> `UNAUTHORIZED`.
    - 403 -> `FORBIDDEN`.
    - 404 -> `NOT_FOUND`.
    - 409 -> `CONFLICT`.
  - message lay tu `exc.detail`.
- 404 route not found:
  - code `NOT_FOUND`.
  - message `Resource not found`.
- Unhandled exception:
  - status `500`.
  - code `INTERNAL_SERVER_ERROR`.
  - message `Internal server error`.
  - log exception voi request id.

Muc dich:

- Loi API co cung format.
- Client va Swagger doc de hon.
- 500 khong lo thong tin noi bo.

## Buoc 8: Dang ky middleware va exception handler trong main.py

File:

```text
app/main.py
```

Can lam:

- Goi `configure_logging()`.
- Add `RequestIDMiddleware`.
- Add `AccessLogMiddleware`.
- Dang ky exception handlers.
- Bo sung metadata FastAPI:
  - title.
  - version.
  - description.
  - contact/license neu muon.

Muc dich:

- Toan app dung chung middleware/handler.
- Swagger/ReDoc hien thong tin du an ro hon.

Luu y:

- Thu tu middleware quan trong.
- Sau khi add exception handler, test cu co the can update neu assert body loi cu.

## Buoc 9: Bo sung API docs cho router

File can xem:

```text
app/api/v1/auth.py
app/api/v1/users.py
app/api/v1/workspaces.py
app/api/v1/projects.py
app/api/v1/tasks.py
app/api/v1/labels.py
app/api/v1/comments.py
```

Can bo sung dan dan:

- `summary`.
- `description` ngan gon.
- `responses` cho cac loi chinh:
  - 400.
  - 401.
  - 403.
  - 404.
  - 409.
  - 422.
- Tag da co thi giu.

Muc dich:

- Swagger khong chi hien endpoint, ma con noi ro endpoint lam gi.
- Demo API cho nguoi khac de hon.

Khuyen nghi:

- Ngay 11 uu tien cac endpoint chinh:
  - auth.
  - users/me.
  - workspace.
  - project.
  - task.
  - label/comment.
- Khong can viet description qua dai trong code.

## Buoc 10: Chuan hoa OpenAPI security

File:

```text
app/api/v1/dependencies.py
app/main.py
```

Can kiem tra:

- `OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")` da dung.
- Swagger authorize hoat dong voi username/password form login.
- Protected endpoint hien icon lock trong Swagger.

Muc dich:

- Demo login bang Swagger thuan tien.
- Nguoi dung biet endpoint nao can Bearer token.

## Buoc 11: Tao seed script demo

File de xuat:

```text
app/scripts/seed_demo.py
```

Hoac:

```text
scripts/seed_demo.py
```

Nen tao du lieu:

- Admin/user demo neu can.
- 1 workspace.
- 2-3 member voi role OWNER/EDITOR/VIEWER.
- 1 project active.
- 1 project archived.
- Vai task voi status/priority/assignee khac nhau.
- Vai label.
- Vai comment.

Muc dich:

- Demo Swagger nhanh.
- Test manual filter/cache/RBAC nhanh hon.

Lenh goi y:

```powershell
docker compose exec app python -m app.scripts.seed_demo
```

Luu y:

- Script nen idempotent neu co the.
- Khong dung password that.
- Du lieu demo nen ghi ro trong README hoac comment.

## Buoc 12: Viet integration test luong chinh

File de xuat:

```text
tests/test_integration_flow.py
```

Test nen co:

- Register owner.
- Login owner lay access token.
- Tao workspace.
- Tao editor/viewer user.
- Add member vao workspace.
- Tao project.
- Tao task.
- Update task assign editor.
- Tao label.
- Attach label vao task.
- Tao comment.
- List task voi filter.
- List comment.
- Xoa comment cua minh.
- Viewer doc duoc project/task/comment.
- Viewer khong update task.

Muc dich:

- Dam bao cac module lien ket that.
- Bat loi route include/dependency/permission/cascade/cache bi lech nhau.

## Buoc 13: Test exception format

File de xuat:

```text
tests/test_error_handling.py
```

Test nen co:

- Validation fail email sai format tra `422` va co:
  - `code`.
  - `message`.
  - `details`.
  - `request_id`.
- Goi protected endpoint khong token tra `401`.
- Goi route khong ton tai tra `404`.
- Business conflict, vi du register email trung, tra `409`.
- Response co header `X-Request-ID`.
- Neu gui header `X-Request-ID`, response tra lai dung value.

Muc dich:

- Dam bao format loi dung nhu docs.
- Dam bao middleware request id hoat dong.

## Buoc 14: Kiem tra logs trong Docker

Chay:

```powershell
docker compose logs app --tail=100
```

Sau do goi vai request:

```powershell
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/not-found
```

Can thay:

- Co access log cho request.
- Co request id.
- Co duration.
- Loi 404/500 khong in data nhay cam.

Muc dich:

- Xac nhan middleware khong chi pass test ma log that trong container.

## Buoc 15: Cap nhat docs/README neu can

File de xuat:

```text
README.md
```

Hoac tao:

```text
docs/API_ERRORS.md
docs/LOGGING.md
```

Noi dung nen co:

- Error response format.
- Request ID header.
- Cach xem log.
- Cach chay seed demo.
- Cach dung Swagger authorize.

Muc dich:

- Ngay 12 delivery chi can tong hop lai, khong phai viet docs tu dau.

## Buoc 16: Chay kiem tra sau khi code

Chay:

```powershell
docker compose exec app pytest -q tests/test_error_handling.py
docker compose exec app pytest -q tests/test_integration_flow.py
docker compose exec app pytest -q
docker compose exec app ruff check app tests
docker compose exec app mypy app tests
docker compose logs app --tail=100
```

Neu co seed script:

```powershell
docker compose exec app python -m app.scripts.seed_demo
```

## Definition of Done ngay 11

Ngay 11 hoan thanh khi:

- Co error response schema dung chung.
- Validation/HTTP/404/500 error tra format nhat quan.
- Moi response co `X-Request-ID`.
- Access log co method/path/status/duration/request id.
- Khong log password/token.
- Swagger/ReDoc co metadata va error responses ro hon.
- Bearer auth tren Swagger van hoat dong.
- Co integration test luong chinh auth -> workspace -> project -> task -> label/comment.
- Co test error handling/request id.
- Co seed script hoac fixture demo nhanh.
- `pytest`, `ruff`, `mypy` pass.

## Rui ro can luu y

- Test cu co the fail vi response body loi thay doi.
- Middleware neu thu tu sai co the lam mat request id trong error response.
- Handler `Exception` neu viet qua rong co the che mat loi trong test; can log exception day du.
- Access log khong nen doc request body vi co the lam anh huong request stream va lo password/token.
- Swagger docs bo sung qua nhieu response lap lai co the lam code router dai; co the tao helper response docs dung chung.

## Ghi chu cho ngay 12

Ngay 12 se review/refactor/optimization va delivery. Ngay 11 nen uu tien chuan hoa van hanh va docs de ngay 12 tap trung vao README, production Dockerfile, clean setup va kiem tra clone lai tu dau.
