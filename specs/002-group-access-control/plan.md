# Implementation Plan: Group-Based Access Control

**Branch**: `002-group-access-control` | **Date**: 2026-06-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-group-access-control/spec.md`

## Summary

Add group-based access control to D1 and D2. Keycloak is extended with six flat application-specific groups (`d1:rrhh`, `d1:worker`, `d1:admin`, `d2:viewer`, `d2:editor`, `d2:admin`). On each OIDC login, each application's backend reads the `groups` JWT claim, filters to its own prefix, and syncs those groups to Django's built-in `auth.Group` membership. A new `require_groups(allowed_groups)` decorator enforces OR-logic group access on views, redirecting unauthorized users to a dedicated access-denied page.

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

### Existing routes preserved

| App | Existing routes | Status |
|-----|----------------|--------|
| D1 | `/` → HomeView (no auth) | Kept as-is |
| D1 | `/dashboard/` → DashboardView (login required) | Kept as-is |
| D1 | `/admin-panel/` → AdminPanelView (login required) | Kept as-is |
| D2 | `/` → HomeView (login required) | Kept as-is |
| D2 | `/reports/` → ReportsView (scope: read:reports) | Gets group decorator added |
| D2 | `/data/` → DataView (scope: write:data) | Kept as-is (scope-only, no group control per spec) |

## Implementation Phases

### Phase A — Keycloak

1. Add 6 flat groups to `keycloak/realm-export.json`
2. Assign test users to groups: `testadmin` → `d1:admin` + `d2:admin`; `testuser` → `d1:worker` + `d2:viewer`
3. Verify group mapper already exists in both clients (confirmed: `groups` mapper present)

### Phase B — D1 Backend & Decorator

1. Extend `d1/accounts/backends.py → update_user()`:
   - Filter `claims['groups']` to `d1:*` prefixed entries
   - `get_or_create` each as Django `auth.Group`
   - Call `user.groups.set(django_groups)` (replaces, handles removals)
2. Create `d1/accounts/decorators.py` with `require_groups(allowed_groups)`:
   - If not authenticated → redirect to `LOGIN_URL`
   - If authenticated but `user.groups.filter(name__in=allowed_groups).exists()` is False → redirect to `/access-denied/?required=<comma-joined-groups>`
   - Otherwise → call the view

### Phase C — D1 Views & Templates

1. Add to `d1/dashboard/views.py`:
   - `D1HomeView` (LoginRequiredMixin + `require_groups(['d1:rrhh','d1:worker','d1:admin'])`)
   - `RRHHView` (`require_groups(['d1:rrhh','d1:admin'])`)
   - `WorkerView` (`require_groups(['d1:worker','d1:admin'])`)
   - `D1AdminView` (`require_groups(['d1:admin'])`)
   - `GroupAccessDeniedView` (unauthenticated, reads `?required=` param)
2. Add URL patterns to `d1/dashboard/urls.py`:
   - `/home/`, `/rrhh/`, `/worker/`, `/admin/` (app-level, not Django admin), `/access-denied/`
3. Create 5 templates

### Phase D — D2 Backend, Decorator & Views

1. Extend `d2/accounts/backends.py → update_user()` and `create_user()`:
   - Same pattern as D1 but filter to `d2:*` groups
2. Add `require_groups(allowed_groups)` to `d2/accounts/decorators.py` (alongside `require_scope`)
3. Update `d2/portal/views.py`:
   - `ReportsView`: add `require_groups(['d2:viewer','d2:editor','d2:admin'])` on top of existing `require_scope`
   - Add `EditorView` with `require_groups(['d2:editor','d2:admin'])`
   - Add `D2AdminView` with `require_groups(['d2:admin'])`
   - Add `GroupAccessDeniedView`
4. Add `/editor/`, `/admin/`, `/group-denied/` to `d2/portal/urls.py`
5. Create 3 new templates

### Phase E — Tests

Each new view needs at minimum:
- Authenticated user with correct group → 200
- Authenticated user without correct group → redirect to access-denied
- Unauthenticated user → redirect to login

Backend tests:
- `update_user()` with groups in claims → `auth.Group` membership set
- `update_user()` with empty groups → `auth.Group` membership cleared
- Only own-prefix groups synced (cross-app groups not leaked)
