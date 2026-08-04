# API Errors va Request ID

Tai lieu nay mo ta format loi thong nhat cua TaskHub API.

## Error Response Format

Tat ca loi API nen tra ve theo format:

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
  "request_id": "9b0f2c7d-8f4e-4cc0-a9d1-123456789abc"
}
```

Y nghia field:

- `code`: ma loi on dinh de client/frontend xu ly.
- `message`: thong bao ngan gon cho nguoi dung/dev.
- `details`: thong tin chi tiet, thuong dung cho validation error.
- `request_id`: id dung de doi chieu voi log trong Docker.

## Ma Loi Chinh

| HTTP status | code | Khi nao xay ra |
| --- | --- | --- |
| 400 | `BAD_REQUEST` | Input dung format nhung sai business rule |
| 401 | `UNAUTHORIZED` | Chua login, token sai hoac token het han |
| 403 | `FORBIDDEN` | Da login nhung khong du quyen |
| 404 | `NOT_FOUND` | Route/resource khong ton tai trong scope |
| 409 | `CONFLICT` | Du lieu trung hoac resource conflict |
| 422 | `VALIDATION_ERROR` | Body/query/path sai validation |
| 500 | `INTERNAL_SERVER_ERROR` | Loi ngoai du kien trong server |

## Request ID Header

Header dung chung:

```text
X-Request-ID
```

Quy tac:

- Neu client gui `X-Request-ID`, API tra lai dung id do.
- Neu client khong gui, API tu tao UUID moi.
- Response header luon co `X-Request-ID`.
- Error response body co field `request_id`.

Vi du:

```powershell
curl.exe -i -H "X-Request-ID: demo-request-1" http://localhost:8000/api/v1/not-found
```

Response se co:

```text
x-request-id: demo-request-1
```

Va body:

```json
{
  "code": "NOT_FOUND",
  "message": "Resource not found",
  "details": null,
  "request_id": "demo-request-1"
}
```

## Vi Du Kiem Tra Nhanh

Validation error:

```powershell
curl.exe -i -X POST http://localhost:8000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"not-an-email\",\"password\":\"password123\",\"full_name\":\"Test\"}"
```

Route not found:

```powershell
curl.exe -i http://localhost:8000/api/v1/not-found
```

Protected endpoint khong token:

```powershell
curl.exe -i http://localhost:8000/api/v1/users/me
```
