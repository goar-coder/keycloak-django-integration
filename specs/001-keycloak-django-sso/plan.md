# Implementation Plan: Keycloak-Django SSO Platform

**Branch**: `001-keycloak-django-sso` | **Date**: 2026-06-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-keycloak-django-sso/spec.md`

## Summary

Build a fully Dockerized SSO platform with Keycloak 24 as the identity provider, two independent Django 5 web applications (D1: main app + Keycloak user management; D2: scope authorization demo), and a shared PostgreSQL 16 database. All user authentication is delegated to Keycloak via OIDC Authorization Code Flow — Django never stores passwords. D1 uses `mozilla-django-oidc` for SSO and `python-keycloak` to manage Keycloak users from protected JSON views. D2 enforces OAuth2 scope-based page access using scopes stored in the OIDC session. The platform starts fully configured from `docker compose up` via a PostgreSQL init script and Keycloak realm auto-import.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**:
- Keycloak 24.0 (`quay.io/keycloak/keycloak:24.0`) — identity provider
- Django 5.1 — web framework for both D1 and D2
- mozilla-django-oidc 4.x — OIDC Authorization Code Flow, session management, token validation
- python-keycloak 3.x — Keycloak Admin REST API client (D1 only, isolated to `kc_admin/client.py`)
- django-environ 0.11+ — environment variable → settings mapping
- PyJWT 2.x — JWT decode for scope extraction (D2)
- psycopg2-binary — PostgreSQL adapter
- gunicorn — WSGI server inside containers
- whitenoise — static file serving

**Storage**: PostgreSQL 16 — 3 isolated logical databases in one container:
- `keycloak_db` / user `keycloak_user` — used by Keycloak
- `d1_db` / user `d1_user` — used by D1
- `d2_db` / user `d2_user` — used by D2
Each user has CONNECT + all privileges on its own database only.

**Testing**: pytest 8.x + pytest-django. Integration tests require live Keycloak + PostgreSQL (run via the full Docker Compose stack or a dedicated test profile). Unit tests can run without Docker using mocked OIDC responses.

**Target Platform**: Linux containers (Docker / Docker Compose). Local development via `docker compose up`. Any Docker-compatible host for deployment.

**Project Type**: Multi-service containerized web application — 2× Django web apps + Keycloak IdP + PostgreSQL, orchestrated by a single `docker-compose.yml`.

**Performance Goals**: End-to-end login flow under 5 seconds (SC-002). No throughput target defined for v1.

**Constraints**:
- No Django REST Framework — all JSON via plain `JsonResponse`
- No JavaScript frameworks — Django template engine only
- No password storage in Django — `set_unusable_password()` enforced
- All secrets via environment variables — `.env` file, never committed
- OIDC token validated by mozilla-django-oidc on every request via session middleware
- `KEYCLOAK_VERIFY_SSL=false` allowed for local development only

**Scale/Scope**: Development / small team (tens to low hundreds of users). No horizontal scaling for v1.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate Criteria | Status | Notes |
|-----------|--------------|--------|-------|
| I. Security-First | No passwords in Django; secrets via env vars only; tokens validated every request; no credential logging | ✅ PASS | `set_unusable_password()` enforced in OIDC backend. All secrets from env. mozilla-django-oidc validates session token on every authenticated view. Logging config excludes sensitive headers/tokens. |
| II. Standards-Based Integration | OIDC Authorization Code Flow; JWKS endpoint for RS256 token verification; no proprietary auth workarounds | ✅ PASS | mozilla-django-oidc uses `OIDC_OP_JWKS_ENDPOINT` for RSA key verification. Standard `/oidc/` endpoints. No Keycloak-specific SDK for authentication — only for Admin API operations. |
| III. Test-First (NON-NEGOTIABLE) | Tests written and verified to FAIL before implementation; integration tests use real Keycloak | ✅ PASS | tasks.md will enforce: write test → confirm failure → implement → pass. Integration tests run against Docker Compose stack. |
| IV. Minimal Coupling | All Keycloak Admin API calls isolated to `d1/kc_admin/client.py`; all config externalized | ✅ PASS | `client.py` is the single integration boundary. Views call `client.py` functions only — never `KeycloakAdmin` directly. All URLs, realm names, client IDs from env vars. |
| V. Observability & Audit | All auth events logged with structured logging: login, logout, token failures, Admin API calls and errors | ✅ PASS | Custom OIDC backend hooks log every auth event. `kc_admin/client.py` logs every Admin API call and error with structured context. No silent failures. |

**Post-Phase 1 re-check**: ✅ All gates still pass. Design artifacts (data-model, contracts) introduce no new violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-keycloak-django-sso/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── d1-web-pages.md  # Phase 1 output
│   ├── d1-admin-api.md  # Phase 1 output
│   └── d2-web-pages.md  # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
keycloak-django-sso/
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── postgres/
│   └── init.sql                     ← Creates 3 DBs + 3 users on first run
│
├── keycloak/
│   └── realm-export.json            ← app-realm config, auto-imported on start
│
├── d1/                              ← Main web app (auth + user management)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── accounts/                    ← OIDC auth + UserProfile sync
│   │   ├── backends.py              ← Custom OIDCAuthenticationBackend
│   │   ├── models.py                ← UserProfile (sub, email, roles, groups)
│   │   ├── views.py                 ← Profile page, logout
│   │   ├── urls.py
│   │   ├── migrations/
│   │   └── tests/
│   │       ├── test_backends.py
│   │       └── test_views.py
│   ├── dashboard/                   ← Protected web pages
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── templates/dashboard/
│   │   └── tests/
│   │       └── test_views.py
│   └── kc_admin/                    ← Keycloak Admin API integration (isolated)
│       ├── client.py                ← ONLY file that calls python-keycloak
│       ├── views.py                 ← JsonResponse views (login required)
│       ├── urls.py
│       └── tests/
│           ├── test_client.py
│           └── test_views.py
│
└── d2/                              ← Scope testing web app
    ├── Dockerfile
    ├── requirements.txt
    ├── manage.py
    ├── config/
    │   ├── settings/
    │   │   ├── base.py
    │   │   ├── development.py
    │   │   └── production.py
    │   ├── urls.py
    │   └── wsgi.py
    ├── accounts/                    ← OIDC auth + scope storage
    │   ├── backends.py              ← Stores scopes in session on login
    │   ├── decorators.py            ← @require_scope("read:reports")
    │   ├── mixins.py                ← ScopeRequiredMixin for CBVs
    │   ├── views.py                 ← Login/logout/denied views
    │   ├── urls.py
    │   └── tests/
    │       ├── test_backends.py
    │       └── test_decorators.py
    └── portal/                      ← Scope-protected pages
        ├── views.py
        ├── urls.py
        ├── templates/portal/
        │   ├── home.html
        │   ├── reports.html
        │   ├── data.html
        │   └── denied.html
        └── tests/
            └── test_views.py
```

**Structure Decision**: Independent Django project per service (D1, D2). No shared Django code — each app has its own `accounts/` app for OIDC backends. Keycloak Admin API is isolated to `d1/kc_admin/client.py` (Principle IV). No monorepo tooling needed at this scale.

## Complexity Tracking

> No constitution violations — section left blank intentionally.
