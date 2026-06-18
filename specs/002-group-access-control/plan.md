# Implementation Plan: Group-Based Access Control

**Branch**: `002-group-access-control` | **Date**: 2026-06-17 | **Updated**: 2026-06-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-group-access-control/spec.md`

## Summary

Add group-based access control to D1 and D2. Keycloak is extended with ten flat application-specific groups (`d1:rrhh`, `d1:worker`, `d1:data`, `d1:admin`, `d2:viewer`, `d2:report`, `d2:editor`, `d2:data`, `d2:admin`, `admin:data`). On each OIDC login, each application's backend reads the `groups` JWT claim, filters to its own prefixes (`d1:*`+`admin:*` for D1, `d2:*`+`admin:*` for D2), and syncs those groups to Django's built-in `auth.Group` membership. A `require_groups(allowed_groups)` decorator enforces OR-logic group access on views. App-level access (which users can log into which app) is controlled via Keycloak Client Roles (`can-login`) enforced in a custom Keycloak Authentication Flow — not in Django.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Django 5.x, mozilla-django-oidc (latest), django.contrib.auth (built-in Group model)

**Storage**: PostgreSQL 16 — `d1_db` (D1), `d2_db` (D2). No new tables required; uses existing `auth_group` and `auth_user_groups` junction tables already created by Django's default migrations.

**Testing**: Django test client (`django.test`). Existing test structure: `accounts/tests/`, `dashboard/tests/`, `portal/tests/`.

**Target Platform**: Linux container (Docker, gunicorn)

**Project Type**: Two separate Django web applications (d1, d2), each in its own container.

**Performance Goals**: Standard Django request/response. Group check is a single indexed DB query per request (`auth_user_groups` + `auth_group`).

**Constraints**: Groups must be re-synced on every login. No mid-session group updates. Each app sees only its own prefix.

**Scale/Scope**: Small team deployment. Six groups total across both apps, expandable by prefix convention.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Rule | Status | Notes |
|------|--------|-------|
| NEVER store passwords in Django | ✅ Pass | No password storage introduced |
| Auth 100% Keycloak | ✅ Pass | Group source of truth is Keycloak; Django groups are a synced cache |
| NEVER commit secrets | ✅ Pass | No new secrets introduced |
| JWT tokens validated against Keycloak on every request | ✅ Pass | mozilla-django-oidc `SessionRefresh` middleware already enforces this |
| All views that require login use `@login_required` or equivalent | ✅ Pass | `require_groups` decorator wraps `login_required`; class-based views use `LoginRequiredMixin` |
| Every service in its own container, single docker-compose.yml | ✅ Pass | No infrastructure changes needed |
| Settings via environment variables | ✅ Pass | No new settings values needed |
| Every view must have at least one test | ⚠️ Required | New views must have tests — tracked in tasks |

## Project Structure

### Documentation (this feature)

```text
specs/002-group-access-control/
├── plan.md              ← this file
├── research.md          ← Phase 0
├── data-model.md        ← Phase 1
├── quickstart.md        ← Phase 1
└── tasks.md             ← Phase 2 (/speckit-tasks)
```

### Source Code changes

```text
keycloak/
└── realm-export.json          ← add 6 groups + update test user assignments

d1/
├── accounts/
│   ├── backends.py            ← extend update_user() to sync d1:* → auth.Group
│   └── decorators.py          ← NEW: require_groups(allowed_groups)
├── dashboard/
│   ├── views.py               ← add RRHHView, WorkerView, D1AdminView, D1HomeView
│   └── urls.py                ← add /home/, /rrhh/, /worker/, /admin/
└── templates/dashboard/
    ├── home_groups.html        ← new group-gated home page
    ├── rrhh.html               ← new
    ├── worker.html             ← new
    ├── admin_section.html      ← new
    └── access_denied.html      ← new (group denial page)

d2/
├── accounts/
│   ├── backends.py            ← extend update_user()/create_user() to sync d2:* → auth.Group
│   └── decorators.py          ← add require_groups(allowed_groups) alongside require_scope
├── portal/
│   ├── views.py               ← add group decorator to ReportsView; add EditorView, D2AdminView
│   └── urls.py                ← add /editor/, /admin/
└── templates/portal/
    ├── editor.html             ← new
    ├── admin_section.html      ← new
    └── group_access_denied.html ← new (group denial page, separate from scope denial)
```

### Complete Route Inventory

| App | Route | Groups required | Status |
|-----|-------|-----------------|--------|
| D1 | `/` | none | unchanged |
| D1 | `/dashboard/` | login only | unchanged |
| D1 | `/home/` | `d1:rrhh\|d1:worker\|d1:data\|d1:admin` | ✅ implemented |
| D1 | `/rrhh/` | `d1:rrhh\|d1:admin` | ✅ implemented |
| D1 | `/worker/` | `d1:worker\|d1:admin` | ✅ implemented |
| D1 | `/data/` | `d1:data\|d1:admin\|admin:data` | ✅ implemented |
| D1 | `/admin/` | `d1:admin` | ✅ implemented |
| D1 | `/admin-panel/` | login only | ✅ enhanced (see Phase F) |
| D1 | `/access-denied/` | none | ✅ implemented |
| D2 | `/reports/` | `d2:report` | ✅ implemented |
| D2 | `/editor/` | `d2:editor\|d2:admin` | ✅ implemented |
| D2 | `/data/` | `d2:data\|d2:admin\|admin:data` | ✅ implemented |
| D2 | `/admin/` | `d2:admin` | ✅ implemented |
| D2 | `/group-denied/` | none | ✅ implemented |

## Implementation Phases

### Phase A — Keycloak Groups & Users ✅

1. Added 10 flat groups to `keycloak/realm-export.json`: `d1:rrhh`, `d1:worker`, `d1:data`, `d1:admin`, `d2:viewer`, `d2:report`, `d2:editor`, `d2:data`, `d2:admin`, `admin:data`
2. Added 7 dedicated test users: `d1_user_rrhh`, `d1_user_worker`, `d1_user_data`, `d2_user_report`, `d2_user_data`, `d2_user_editor`, `user_admin_data`

### Phase B — D1 Backend & Decorator ✅

1. `d1/accounts/backends.py → update_user()`: filters `claims['groups']` to `d1:*` and `admin:*`, syncs to `auth.Group` via `user.groups.set()`
2. `d1/accounts/decorators.py`: `require_groups(allowed_groups)` — OR logic, redirects to `/access-denied/?required=...`

### Phase C — D1 Views & Templates ✅

- `D1HomeView`: `require_groups(['d1:rrhh','d1:worker','d1:data','d1:admin'])`
- `RRHHView`: `require_groups(['d1:rrhh','d1:admin'])`
- `WorkerView`: `require_groups(['d1:worker','d1:admin'])`
- `DataView`: `require_groups(['d1:data','d1:admin','admin:data'])`
- `D1AdminView`: `require_groups(['d1:admin'])`
- `GroupAccessDeniedView`: reads `?required=`, renders list

### Phase D — D2 Backend, Decorator & Views ✅

1. `d2/accounts/backends.py`: filters to `d2:*` and `admin:*`
2. `ReportsView`: `require_groups(['d2:report'])` — NOTE: changed from `d2:viewer` to `d2:report`
3. `EditorView`: `require_groups(['d2:editor','d2:admin'])`
4. `DataView`: `require_groups(['d2:data','d2:admin','admin:data'])`
5. `D2AdminView`: `require_groups(['d2:admin'])`

### Phase E — App-Level Access Control via Keycloak Auth Flows ✅

Each Keycloak client (`d1-client`, `d2-client`) has a `can-login` client role. Custom auth flows enforce this role before token issuance.

**Auth flow structure** (same for both clients):
```
[REQUIRED] auth-methods-wrapper        ← wraps all ALTERNATIVEs at top level
    ├── [ALTERNATIVE] Cookie
    ├── [ALTERNATIVE] IDP Redirector
    └── [ALTERNATIVE] Forms (username+password)
[CONDITIONAL] role-check               ← runs after any authentication method
    ├── [REQUIRED] Condition - User Role (negate=true, role=client.can-login)
    └── [REQUIRED] Deny Access (deny-access-authenticator)
```

> **Important**: ALTERNATIVE and CONDITIONAL/REQUIRED executions cannot be mixed at the same top level in Keycloak. All ALTERNATIVEs must be wrapped in a REQUIRED sub-flow first.

**Result**: Django backends have no `verify_claims()` override. Access control is entirely at the Keycloak level for app login, and at the Django group level for route access.

### Phase F — Admin Panel Enhancements ✅

Enhanced `d1/kc_admin/` module:

- **Create User**: now accepts `password` field → sent to Keycloak as `credentials: [{type: password, value: ..., temporary: false}]`
- **Assign Role**: new `GET /api/roles/` endpoint returns realm roles + d1-client + d2-client client roles. Frontend uses `<select>` dropdown.
- **Assign Client Role**: new `assign_client_role()` in `client.py` handles client-scoped role assignment
- **Assign Group**: new `GET /api/groups/` endpoint returns all Keycloak groups. Frontend uses `<select>` dropdown.
- **Service account permissions**: `d1-client` service account granted `view-clients`, `view-realm`, `query-clients`, `query-realms`, `manage-users`, `view-users`, `query-groups` in `realm-management`

### Phase G — Infrastructure ✅

- `docker-compose.yml`: added volume mounts `./d1:/app` and `./d2:/app` — files update in real-time without `docker cp`
- `d1/Dockerfile` and `d2/Dockerfile`: changed `--workers 2` to `--workers 1` — eliminates template caching inconsistency across worker processes

### Phase H — Tests ✅

All views have tests covering: authorized group → 200, unauthorized group → redirect to denied, anonymous → redirect to login. Backend tests cover group sync, cross-app isolation, and group removal.
