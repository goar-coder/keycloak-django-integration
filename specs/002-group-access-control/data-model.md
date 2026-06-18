# Data Model: Group-Based Access Control

**Date**: 2026-06-17
**Feature**: `002-group-access-control`

## No New Django Models

This feature introduces no new database models. It relies entirely on Django's existing built-in models from `django.contrib.auth`:

- `auth_group` — stores group names (e.g., `d1:rrhh`, `d2:admin`)
- `auth_user_groups` — M:N junction between users and groups
- `auth_user` — the existing Django user (no changes)

Both tables already exist in `d1_db` and `d2_db` because `django.contrib.auth` is in `INSTALLED_APPS` and migrations have already run.

---

## Existing Model Used: `django.contrib.auth.models.Group`

| Field | Type | Notes |
|-------|------|-------|
| `id` | AutoField (PK) | Auto-generated |
| `name` | CharField(150), unique | e.g., `d1:rrhh`, `d2:admin` |

**Access via ORM**:
```python
# Check if user has any required group
user.groups.filter(name__in=['d1:rrhh', 'd1:admin']).exists()

# Set user's D1 groups (replaces all, handles removals)
d1_groups = Group.objects.filter(name__startswith='d1:')
user.groups.set(d1_groups)
```

---

## Group Sync Behavior

On every successful OIDC login, the backend:

1. Reads `claims['groups']` from the JWT (list of strings, e.g., `["d1:worker", "d2:viewer"]`)
2. Filters to the current app's prefix (`d1:*` in D1, `d2:*` in D2)
3. For each filtered group name: `get_or_create(name=group_name)` on `auth.Group`
4. Calls `user.groups.set(django_groups)` — atomically replaces the user's group membership

**Removal handling**: `set()` removes any previously held groups not in the new list. If a user is removed from `d1:rrhh` in Keycloak, their next login clears `d1:rrhh` from `auth_user_groups`.

**Cross-app isolation**: D1 only touches groups starting with `d1:`. It never reads, creates, or removes `d2:*` groups. The same applies in reverse for D2.

---

## Keycloak Groups (source of truth)

Six new flat groups added to `realm-export.json`:

| Group name | App | Access |
|------------|-----|--------|
| `d1:rrhh` | D1 | `/rrhh/`, `/home/` |
| `d1:worker` | D1 | `/worker/`, `/home/` |
| `d1:admin` | D1 | `/rrhh/`, `/worker/`, `/admin/`, `/home/` |
| `d2:viewer` | D2 | `/reports/` |
| `d2:editor` | D2 | `/reports/`, `/editor/` |
| `d2:admin` | D2 | `/reports/`, `/editor/`, `/admin/` |

**Format in realm-export.json**:
```json
"groups": [
  { "name": "team-a", "path": "/team-a", "subGroups": [] },
  { "name": "ops",    "path": "/ops",    "subGroups": [] },
  { "name": "d1:rrhh",   "path": "/d1:rrhh",   "subGroups": [] },
  { "name": "d1:worker", "path": "/d1:worker", "subGroups": [] },
  { "name": "d1:admin",  "path": "/d1:admin",  "subGroups": [] },
  { "name": "d2:viewer", "path": "/d2:viewer", "subGroups": [] },
  { "name": "d2:editor", "path": "/d2:editor", "subGroups": [] },
  { "name": "d2:admin",  "path": "/d2:admin",  "subGroups": [] }
]
```

**JWT claim** (mapper already configured, `full.path: false`):
```json
"groups": ["d1:worker", "d2:viewer"]
```

---

## Access Policy Map

### D1

| URL pattern | Required groups (any one) | View class |
|-------------|--------------------------|------------|
| `/home/` | `d1:rrhh`, `d1:worker`, `d1:admin` | `D1HomeView` |
| `/rrhh/` | `d1:rrhh`, `d1:admin` | `RRHHView` |
| `/worker/` | `d1:worker`, `d1:admin` | `WorkerView` |
| `/admin/` | `d1:admin` | `D1AdminView` |
| `/access-denied/` | none (unauthenticated OK) | `GroupAccessDeniedView` |

### D2

| URL pattern | Required groups (any one) | Also requires scope | View class |
|-------------|--------------------------|---------------------|------------|
| `/reports/` | `d2:viewer`, `d2:editor`, `d2:admin` | `read:reports` | `ReportsView` |
| `/editor/` | `d2:editor`, `d2:admin` | none | `EditorView` |
| `/admin/` | `d2:admin` | none | `D2AdminView` |
| `/group-denied/` | none | none | `GroupAccessDeniedView` |

---

## Test User Group Assignments in Realm Export

| User | Keycloak groups | Effective D1 groups | Effective D2 groups |
|------|----------------|---------------------|---------------------|
| `testadmin` | `d1:admin`, `d2:admin`, `ops` | `d1:admin` | `d2:admin` |
| `testuser` | `d1:worker`, `d2:viewer`, `team-a` | `d1:worker` | `d2:viewer` |

`testadmin` can access all group-protected pages in both apps.
`testuser` can access `/home/` and `/worker/` in D1 (not `/rrhh/` or `/admin/`), and `/reports/` in D2 (not `/editor/` or `/admin/`).
