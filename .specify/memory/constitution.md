# Project Constitution

## Project Name
keycloak-django-sso

## Overview
Dockerized project with one Keycloak instance and two Django services.
Authentication and authorization are fully delegated to Keycloak.
No local Django users — all identity lives in Keycloak.

## Architecture

### Services (all Docker containers)
- **keycloak** — Identity Provider (IdP). Single source of truth for users, roles, groups and scopes.
- **d1** — Django web application. User-facing app. Auth via Keycloak (OIDC). Can create/manage Keycloak users via Admin REST API.
- **d2** — Django web application. Scope testing app. Validates and enforces OAuth2 scopes from Keycloak tokens.
- **postgres** — Single shared PostgreSQL server. Each service uses its own database within this instance.

### Database Layout (single PostgreSQL server, separate databases)
| Database | Used by |
|---|---|
| `keycloak_db` | Keycloak |
| `d1_db` | Django D1 |
| `d2_db` | Django D2 |

> Each service connects with its own PostgreSQL user and has no access to the other databases.
> The `postgres` container exposes a single port internally. No service connects to another service's database.

### Auth Flow
- Login for both D1 and D2 is always via Keycloak (OIDC Authorization Code Flow).
- Django does NOT store passwords. No Django local auth backends.
- JWT access tokens from Keycloak are validated on every request.
- D1 syncs Keycloak user data (sub, email, roles, groups) into a local profile model on first login.
- D2 uses token scopes to gate access to pages (scope-based authorization).

### Keycloak Structure
- One Realm: `app-realm`
- Clients: `d1-client` (confidential, Authorization Code), `d2-client` (confidential, Authorization Code)
- Roles: defined per client and at realm level as needed
- Groups: managed in Keycloak, synced to D1 on login
- Scopes: custom scopes defined in Keycloak, assigned per client, tested in D2

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Identity Provider | Keycloak | 24.x |
| Backend | Django | 5.x |
| Django OIDC | mozilla-django-oidc | latest |
| Templates | Django Templates | built-in |
| Database | PostgreSQL | 16 |
| Container | Docker + Docker Compose | latest |
| Python | Python | 3.12 |
| Keycloak Admin API client | python-keycloak | latest |

> No Django REST Framework. D1 and D2 are standard Django web applications with views and templates.
> The ONLY exception is D1's internal Keycloak user management, which uses python-keycloak directly in views — not exposed as a REST API.

## Non-Negotiable Rules

### Security
- NEVER store passwords in Django. Auth is 100% Keycloak.
- NEVER commit secrets. All credentials via environment variables in `.env` files.
- `.env` files are always in `.gitignore`.
- JWT tokens / OIDC sessions must be validated against Keycloak on every request.
- Token expiration must be enforced. No exceptions.
- All views that require login must use the `@login_required` decorator or equivalent OIDC mixin.

### Docker
- Every service runs in its own container.
- All services are defined in a single `docker-compose.yml`.
- The `postgres` container is the ONLY database service. No service has its own database container.
- No service depends on another being fully ready without a proper healthcheck.
- `postgres` healthcheck must pass before Keycloak, D1 or D2 start.
- Keycloak must be healthy before D1 or D2 attempt OIDC discovery.
- Database initialization (create users and databases) runs via an init SQL script mounted into the postgres container.

### Database
- One PostgreSQL server (`postgres` service), three logical databases: `keycloak_db`, `d1_db`, `d2_db`.
- Each database has its own PostgreSQL user with access ONLY to its own database.
- Init script location: `postgres/init.sql` — mounted at `/docker-entrypoint-initdb.d/init.sql`.
- No service is allowed to use the default `postgres` superuser in production.

### Django
- One Django project per service (d1, d2). No shared Django project.
- D1 and D2 are standard Django web applications: views, templates, urls. No DRF.
- D1 also exposes internal API endpoints (Django views returning JSON) for Keycloak user management.
  These are NOT DRF — they are plain Django JsonResponse views, protected by OIDC session.
- Settings split into `base.py`, `development.py`, `production.py`.
- No `DEBUG=True` in production settings.
- All configuration via environment variables (django-environ).
- No hardcoded URLs, ports or credentials anywhere in the codebase.

### Keycloak
- Realm and client configuration exported as JSON and stored in `keycloak/realm-export.json`.
- This export is imported automatically on container start (no manual Keycloak setup needed after first run).
- Keycloak Admin REST API used from D1 views (via python-keycloak) to create/update/delete users.

### Code Quality
- Every view must have at least one test.
- No hardcoded URLs, ports or credentials anywhere in the codebase.

## Project Structure
keycloak-django-sso/

├── docker-compose.yml

├── .env.example

├── postgres/

│   └── init.sql                ← creates databases and users on first run

├── keycloak/

│   └── realm-export.json       ← realm config, auto-imported on start

├── d1/

│   ├── Dockerfile

│   ├── requirements.txt

│   ├── manage.py

│   └── config/

│       └── settings/

│           ├── base.py

│           ├── development.py

│           └── production.py

└── d2/

├── Dockerfile

├── requirements.txt

├── manage.py

└── config/

└── settings/

├── base.py

├── development.py

└── production.py

## Key Capabilities

### D1 — Main Web App
- OIDC login/logout via Keycloak (mozilla-django-oidc)
- On login: sync user sub, email, roles and groups into local UserProfile model
- Views protected with `@login_required` / OIDCLoginRequiredMixin
- Web interface (Django templates) for day-to-day use
- JSON endpoints (plain Django JsonResponse, no DRF) that:
  - Receive a request from the browser or an authorized caller
  - Call the Keycloak Admin REST API via python-keycloak
  - Create, update, assign roles/groups, or deactivate users in Keycloak
  - Return the result as JSON
- All Keycloak Admin API calls are made server-side from D1 — never from the browser directly

### D2 — Scope Testing Web App
- OIDC login/logout via Keycloak
- Pages protected by specific scopes (e.g. `read:reports`, `write:data`)
- Shows a clear access denied page if token does not contain the required scope
- Useful for visually validating Keycloak scope configuration