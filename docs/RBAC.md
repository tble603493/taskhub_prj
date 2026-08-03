# RBAC va Authorization Policy

Tai lieu nay mo ta cach TaskHub phan quyen user theo system role, workspace role va ownership cua resource.

## Role

### System role

`ADMIN`

- Quan tri he thong theo policy rieng.
- Co the duoc dung cho cac API quan tri user/system sau nay.

`USER`

- Role mac dinh cua user.
- Lam viec thong qua workspace membership.

### Workspace role

`OWNER`

- Quan ly workspace va member.
- Co quyen ghi content trong workspace.
- Co the co nhieu owner trong mot workspace.
- Khong duoc remove hoac demote owner cuoi cung.

`EDITOR`

- Co quyen tao/sua/xoa content trong workspace.
- Khong quan ly workspace/member theo policy hien tai.

`VIEWER`

- Chi doc content trong workspace.
- Khong co quyen tao/sua/xoa content.

## Ma Tran Quyen

| Resource | Action | OWNER | EDITOR | VIEWER |
| --- | --- | --- | --- | --- |
| Workspace | Get/List | Yes | Yes | Yes |
| Workspace | Update/Delete | Yes | No | No |
| Workspace Member | List | Yes | Yes | Yes |
| Workspace Member | Add/Update/Remove | Yes | No | No |
| Project | List/Get | Yes | Yes | Yes |
| Project | Create/Update/Archive | Yes | Yes | No |
| Project | Hard Delete | Yes | No | No |
| Task | List/Get | Yes | Yes | Yes |
| Task | Create/Update/Delete | Yes | Yes | No |
| Label | List/Get | Yes | Yes | Yes |
| Label | Create/Update/Delete | Yes | Yes | No |
| Task Label | Attach/Detach | Yes | Yes | No |
| Comment | List/Create | Yes | Yes | Yes |
| Comment | Delete own comment | Yes | Yes | Yes |
| Comment | Delete others' comments | Yes | Yes | No |

## Ownership Rule Cho Comment

Comment co ownership rieng qua `author_id`.

- Author duoc xoa comment cua minh.
- `OWNER` va `EDITOR` duoc xoa comment cua nguoi khac trong cung workspace.
- `VIEWER` khong duoc xoa comment cua nguoi khac.
- User ngoai workspace khong duoc doc, tao hoac xoa comment.

## Project Archived Policy

Project archived la project co:

```text
status = ARCHIVED
```

Project archived khong bi xoa khoi database. Du lieu van co the doc lai theo permission.

Khi project da archived:

- Khong tao/sua/xoa task trong project.
- Khong tao/sua/xoa label trong project.
- Khong gan/bo label cho task trong project.
- Khong tao comment moi trong project.

Muc dich:

- Giu lich su du lieu.
- Tranh xoa nham.
- Cho phep xem lai project cu nhung khong tiep tuc thay doi noi dung.

## HTTP Status Code Policy

### 401 Unauthorized

Dung khi request chua xac thuc hop le.

Cac truong hop:

- Khong gui Bearer token.
- Token sai dinh dang.
- Token het han.
- Token khong decode duoc.
- Token khong phai access token khi goi protected API.

Vi du:

```text
GET /api/v1/users/me
Authorization: <missing>
```

Ket qua:

```text
401 Unauthorized
```

### 403 Forbidden

Dung khi user da dang nhap hop le nhung khong du quyen thao tac.

Cac truong hop:

- User inactive.
- User la member workspace nhung role khong du.
- User khong la member workspace.
- `VIEWER` goi API create/update/delete.
- `EDITOR` goi API chi `OWNER` moi duoc dung.

Vi du:

```text
PATCH /api/v1/workspaces/1
```

Neu user la `EDITOR` hoac `VIEWER`, ket qua:

```text
403 Forbidden
```

### 404 Not Found

Dung khi resource khong ton tai trong scope duoc yeu cau.

Cac truong hop:

- Workspace khong ton tai.
- Project khong ton tai trong workspace.
- Task khong ton tai trong project.
- Label khong ton tai trong project.
- Comment khong ton tai trong task.
- Resource co ton tai nhung khong thuoc parent resource trong URL.

Vi du:

```text
GET /api/v1/workspaces/1/projects/999
```

Neu project `999` khong nam trong workspace `1`, ket qua:

```text
404 Not Found
```

## Ghi Chu Ve Non-Member Workspace

Hien tai TaskHub tra `403 Forbidden` khi user da dang nhap nhung khong phai member cua workspace.

Ly do:

- API da co `workspace_id` trong URL.
- Policy ngay 9 uu tien don gian va ro rang.
- Test hien tai dang cover non-member theo huong `403`.

Sau nay neu muon tranh lo thong tin workspace co ton tai hay khong, co the doi non-member tu `403` sang `404`. Khi doi policy nay, can update lai service va test authorization tuong ung.

## Implementation Notes

Permission helper nam tai:

```text
app/core/permissions.py
```

Dependency lien quan nam tai:

```text
app/api/v1/dependencies.py
```

Service van la noi chinh xu ly business rule va permission cho resource:

- `app/services/workspace.py`
- `app/services/project.py`
- `app/services/task.py`
- `app/services/label.py`
- `app/services/comment.py`
