# Data Model: Group-Based Access Control

**Date**: 2026-06-17 | **Updated**: 2026-06-18
**Feature**: `002-group-access-control`

## No New Django Models

This feature uses Django's built-in `django.contrib.auth` models — no new tables required:

- `auth_group` — stores group names (e.g., `d1:rrhh`, `admin:data`)
- `auth_user_groups` — M:N junction between users and groups
- `auth_user` — existing Django user (unchanged)

---

## Group Sync Behavior

On every successful OIDC login:

1. Reads `claims['groups']` from the JWT
2. Filters to the current app's prefixes:
   - **D1**: keeps `d1:*` and `admin:*`
   - **D2**: keeps `d2:*` and `admin:*`
3. `get_or_create` each as `auth.Group`
4. `user.groups.set(django_groups)` — atomically replaces membership

**Cross-app isolation**: D1 never touches `d2:*` groups; D2 never touches `d1:*` groups. Both apps sync `admin:*` groups.

---

## Keycloak Groups (source of truth)

| Group name   | Prefix   | Apps that sync | Routes granted |
|--------------|----------|----------------|----------------|
| `d1:rrhh`    | d1:      | D1             | `/rrhh/`, `/home/` |
| `d1:worker`  | d1:      | D1             | `/worker/`, `/home/` |
| `d1:data`    | d1:      | D1             | `/data/`, `/home/` |
| `d1:admin`   | d1:      | D1             | all D1 routes |
| `d2:viewer`  | d2:      | D2             | *(legacy — no routes)* |
| `d2:report`  | d2:      | D2             | `/reports/` |
| `d2:editor`  | d2:      | D2             | `/editor/` |
| `d2:data`    | d2:      | D2             | `/data/` |
| `d2:admin`   | d2:      | D2             | all D2 routes |
| `admin:data` | admin:   | D1 + D2        | `/data/` in both apps |

---

## Access Policy Map

### D1

| URL          | Required groups (any one)                  | View class           |
|--------------|--------------------------------------------|----------------------|
| `/home/`     | `d1:rrhh`, `d1:worker`, `d1:data`, `d1:admin` | `D1HomeView`      |
| `/rrhh/`     | `d1:rrhh`, `d1:admin`                      | `RRHHView`           |
| `/worker/`   | `d1:worker`, `d1:admin`                    | `WorkerView`         |
| `/data/`     | `d1:data`, `d1:admin`, `admin:data`        | `DataView`           |
| `/admin/`    | `d1:admin`                                 | `D1AdminView`        |
| `/access-denied/` | none                                  | `GroupAccessDeniedView` |

### D2

| URL           | Required groups (any one)                  | View class              |
|---------------|--------------------------------------------|-------------------------|
| `/reports/`   | `d2:report`                                | `ReportsView`           |
| `/editor/`    | `d2:editor`, `d2:admin`                    | `EditorView`            |
| `/data/`      | `d2:data`, `d2:admin`, `admin:data`        | `DataView`              |
| `/admin/`     | `d2:admin`                                 | `D2AdminView`           |
| `/group-denied/` | none                                    | `GroupAccessDeniedView` |

---

## Keycloak Client Roles (App-Level Access Control)

Each Keycloak client has a `can-login` client role. This is enforced in a **custom Authentication Flow** — users without this role cannot complete login to that app.

| Client      | Role        | Effect |
|-------------|-------------|--------|
| `d1-client` | `can-login` | Required to log into D1 |
| `d2-client` | `can-login` | Required to log into D2 |

The custom auth flow structure:
```
[REQUIRED] auth-methods-wrapper
    ├── [ALTERNATIVE] Cookie
    ├── [ALTERNATIVE] IDP Redirector
    └── [ALTERNATIVE] Forms
[CONDITIONAL] role-check
    ├── [REQUIRED] Condition - User Role (negate=true, role=client.can-login)
    └── [REQUIRED] Deny Access (provider: deny-access-authenticator)
```

---

## Admin Panel API

The `d1-client` service account has these `realm-management` roles to support the admin panel:

| Role           | Purpose |
|----------------|---------|
| `view-users`   | List users |
| `manage-users` | Create users, list groups |
| `view-clients` | List clients for role lookup |
| `view-realm`   | List realm roles |
| `query-clients`| Query client by ID |
| `query-realms` | Query realm metadata |
| `query-groups` | Query groups |

New admin panel API endpoints:

| Endpoint            | Method | Purpose |
|---------------------|--------|---------|
| `GET /api/users/`   | GET    | List all Keycloak users |
| `POST /api/users/create/` | POST | Create user with password |
| `POST /api/users/<sub>/roles/assign/` | POST | Assign realm or client role |
| `POST /api/users/<sub>/groups/assign/` | POST | Assign group |
| `POST /api/users/<sub>/deactivate/` | POST | Disable user |
| `GET /api/roles/`   | GET    | List assignable roles (realm + d1-client + d2-client) |
| `GET /api/groups/`  | GET    | List all Keycloak groups alphabetically |

---

## Test Users

| Username          | Keycloak groups     | D1 login | D2 login | D1 Django groups           | D2 Django groups    |
|-------------------|---------------------|----------|----------|----------------------------|---------------------|
| `testadmin`       | `d1:admin`, `d2:admin`, `ops` | ✅ | ✅ | `d1:admin` | `d2:admin` |
| `testuser`        | `d1:worker`, `d2:viewer`, `team-a` | ✅ | ✅ | `d1:worker` | *(none — d2:viewer grants nothing)* |
| `d1_user_rrhh`    | `d1:rrhh`           | ✅       | ❌       | `d1:rrhh`                  | —                   |
| `d1_user_worker`  | `d1:worker`         | ✅       | ❌       | `d1:worker`                | —                   |
| `d1_user_data`    | `d1:data`           | ✅       | ❌       | `d1:data`                  | —                   |
| `d2_user_report`  | `d2:report`         | ❌       | ✅       | —                          | `d2:report`         |
| `d2_user_data`    | `d2:data`           | ❌       | ✅       | —                          | `d2:data`           |
| `d2_user_editor`  | `d2:editor`         | ❌       | ✅       | —                          | `d2:editor`         |
| `user_admin_data` | `admin:data`        | ✅       | ✅       | `admin:data`               | `admin:data`        |

✅/❌ in login columns reflects whether the user has `can-login` client role for that app.
