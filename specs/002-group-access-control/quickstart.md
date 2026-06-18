# Quickstart Validation Guide: Group-Based Access Control

**Feature**: `002-group-access-control`
**Date**: 2026-06-17

This guide validates the group-based access control feature end-to-end. It assumes the platform is already running (`docker compose up`). See [spec.md](spec.md) and [data-model.md](data-model.md) for full context.

---

## Prerequisites

- Platform running: `docker compose up --build`
- All 4 services healthy: `docker compose ps`
- A full reset is required after realm-export.json changes:
  ```bash
  docker compose down -v && docker compose up --build
  ```

---

## Test Users After Realm Update

| User | Password | D1 access | D2 access |
|------|----------|-----------|-----------|
| `testadmin` | `testadmin123` | `/home/` `/rrhh/` `/worker/` `/admin/` | `/reports/` `/editor/` `/admin/` |
| `testuser` | `testuser123` | `/home/` `/worker/` only | `/reports/` only |

---

## VS1 — Keycloak groups imported correctly

```bash
# Get admin token
TOKEN=$(curl -s -X POST http://localhost:8080/realms/master/protocol/openid-connect/token \
  -d "client_id=admin-cli&username=admin&password=admin123&grant_type=password" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# List groups in app-realm
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/admin/realms/app-realm/groups \
  | python3 -c "import sys,json; [print(g['name']) for g in json.load(sys.stdin)]"
```

Expected: `d1:rrhh`, `d1:worker`, `d1:admin`, `d2:viewer`, `d2:editor`, `d2:admin` (plus existing `team-a`, `ops`).

---

## VS2 — testadmin has correct group assignments

```bash
# Get testadmin's groups
ADMIN_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/admin/realms/app-realm/users?username=testadmin" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/admin/realms/app-realm/users/$ADMIN_ID/groups" \
  | python3 -c "import sys,json; [print(g['name']) for g in json.load(sys.stdin)]"
```

Expected: includes `d1:admin` and `d2:admin`.

---

## VS3 — D1 group sync on login (testuser)

1. Log in to D1 at `http://localhost:8001/` with `testuser / testuser123`
2. Verify Django synced the groups:

```bash
docker compose exec d1 python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.get(username='testuser')
print([g.name for g in u.groups.all()])
"
```

Expected: `['d1:worker']` (only D1-prefixed groups — D2 groups are not synced to D1).

---

## VS4 — D1 testuser access matrix

Log in as `testuser`. In the browser:

| URL | Expected |
|-----|----------|
| `http://localhost:8001/home/` | ✅ 200 (has `d1:worker`) |
| `http://localhost:8001/worker/` | ✅ 200 (has `d1:worker`) |
| `http://localhost:8001/rrhh/` | ❌ access-denied page |
| `http://localhost:8001/admin/` | ❌ access-denied page |

The access-denied page at `/access-denied/` must:
- Be a rendered HTML page (not a 500)
- Show the groups required for the last requested page

---

## VS5 — D1 testadmin full access

Log in as `testadmin`. In the browser:

| URL | Expected |
|-----|----------|
| `http://localhost:8001/home/` | ✅ 200 |
| `http://localhost:8001/rrhh/` | ✅ 200 |
| `http://localhost:8001/worker/` | ✅ 200 |
| `http://localhost:8001/admin/` | ✅ 200 |

---

## VS6 — D2 group sync on login (testuser)

1. Log in to D2 at `http://localhost:8002/` with `testuser / testuser123` (or auto-login from VS4 if same browser)
2. Verify Django synced the groups:

```bash
docker compose exec d2 python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.get(username='testuser')
print([g.name for g in u.groups.all()])
"
```

Expected: `['d2:viewer']` (only D2-prefixed groups — D1 groups are not synced to D2).

---

## VS7 — D2 testuser access matrix

Log in as `testuser`. In the browser:

| URL | Expected |
|-----|----------|
| `http://localhost:8002/reports/` | ✅ 200 (has `d2:viewer` + `read:reports` scope needed — see note) |
| `http://localhost:8002/editor/` | ❌ group-denied page |
| `http://localhost:8002/admin/` | ❌ group-denied page |

> **Note on `/reports/`**: The `ReportsView` requires BOTH the `read:reports` scope AND group membership. If `testuser` was not granted the `read:reports` scope, they will hit the scope-denied page (`/denied/`) before the group check. Grant the scope in Keycloak admin if needed (see VS8 in [main quickstart](../../001-keycloak-django-sso/quickstart.md)).

---

## VS8 — D2 testadmin full access

Log in as `testadmin`. In the browser:

| URL | Expected |
|-----|----------|
| `http://localhost:8002/reports/` | ✅ 200 |
| `http://localhost:8002/editor/` | ✅ 200 |
| `http://localhost:8002/admin/` | ✅ 200 |

---

## VS9 — Authenticated user with no groups sees access-denied (not login redirect)

1. In Keycloak admin, create a user `testguest / testguest123` with no groups
2. Log in to D1 at `http://localhost:8001/`
3. Navigate to `http://localhost:8001/home/`

Expected: access-denied page (not the Keycloak login screen).

Alternative (no new user needed): Remove `testuser` from all groups in Keycloak admin, log out, and log back in.

---

## VS10 — Group change takes effect on re-login

1. Log in as `testuser` in D1
2. Confirm `/rrhh/` shows access-denied
3. In Keycloak admin, add `testuser` to group `d1:rrhh`
4. Log out of D1
5. Log back in as `testuser`
6. Navigate to `/rrhh/`

Expected: `/rrhh/` now shows 200. No application restart required.

7. Reverse: remove `testuser` from `d1:rrhh` in Keycloak, log out, log in again
8. Navigate to `/rrhh/`

Expected: access-denied page again.

---

## VS11 — Cross-app group isolation

While logged in as `testuser`:

```bash
# D1 should only have d1:* groups
docker compose exec d1 python manage.py shell -c "
from django.contrib.auth import get_user_model
u = get_user_model().objects.get(username='testuser')
names = [g.name for g in u.groups.all()]
assert all(n.startswith('d1:') for n in names), f'Unexpected groups: {names}'
print('D1 groups OK:', names)
"

# D2 should only have d2:* groups
docker compose exec d2 python manage.py shell -c "
from django.contrib.auth import get_user_model
u = get_user_model().objects.get(username='testuser')
names = [g.name for g in u.groups.all()]
assert all(n.startswith('d2:') for n in names), f'Unexpected groups: {names}'
print('D2 groups OK:', names)
"
```

Expected: Both assertions pass. No cross-app group leakage.

---

## VS12 — Running the test suite

```bash
# D1 tests (includes new backend and view tests)
docker compose exec d1 python manage.py test --verbosity=2

# D2 tests (includes new backend, decorator, and view tests)
docker compose exec d2 python manage.py test --verbosity=2
```

Expected: All tests pass, zero failures or errors.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Groups not synced after login | User had an existing session; sync only on re-login | Log out completely, log back in |
| `d1:*` groups appear in D2 or vice versa | Backend prefix filter missing | Check that D2 backend filters `d2:*` only |
| Access-denied page not found (404) | URL pattern missing | Verify `/access-denied/` in D1 urls.py and `/group-denied/` in D2 urls.py |
| Groups empty in Django after login | JWT `groups` claim empty | Verify user has groups assigned in Keycloak; check group mapper on the client |
| Full reset needed | realm-export.json changed | `docker compose down -v && docker compose up --build` |
