# Research: Keycloak-Django SSO Platform

**Feature**: `001-keycloak-django-sso`
**Date**: 2026-06-16

All unknowns were resolved without external research — the user provided an explicit and complete tech stack. This document records the key technical decisions and their rationale.

---

## Decision 1: OIDC Library — mozilla-django-oidc

**Decision**: Use `mozilla-django-oidc` for OIDC Authorization Code Flow in both D1 and D2.

**Rationale**:
- Production-grade, actively maintained, designed for Django
- Uses Keycloak's JWKS endpoint (`OIDC_OP_JWKS_ENDPOINT`) for RS256 token verification — aligns directly with Principle II (Standards-Based Integration)
- Session-based: stores only a session key in the cookie, not raw tokens
- Provides clean hooks: `OIDCAuthenticationBackend.create_user()` and `update_user()` — the exact extension points needed for UserProfile sync (US2)
- `OIDC_STORE_ACCESS_TOKEN = True` makes the raw access token available in session for scope extraction (needed by D2)

**Alternatives considered**:
- `social-auth-app-django` — more complex config, heavier dependency tree, less OIDC-native
- `authlib` — excellent library but lower-level; would require more manual session plumbing
- Raw OIDC implementation — too much maintenance burden for no added benefit

---

## Decision 2: Scope Enforcement in D2 (without DRF)

**Decision**: Store scopes in the Django session at login time. Enforce with a `@require_scope` decorator and `ScopeRequiredMixin`.

**Mechanism**:
1. Set `OIDC_STORE_ACCESS_TOKEN = True` in D2 settings
2. Override `OIDCAuthenticationBackend.create_user()` and `update_user()` in `d2/accounts/backends.py`:
   - Decode the stored access token with PyJWT (no verification needed — Keycloak already validated it)
   - Extract `scope` claim (space-separated string per RFC 6749) or `realm_access.roles`
   - Store as list in session: `request.session['oidc_scopes'] = token_scopes`
3. `@require_scope("read:reports")` decorator checks `request.session.get('oidc_scopes', [])` and redirects to `/denied/` if scope absent

**Why session storage over per-request decoding**:
- D2 is a demo app — session freshness acceptable
- Avoids PyJWT decode on every request
- Consistent with how mozilla-django-oidc manages session state

**Alternatives considered**:
- Decode JWT on every request: accurate but adds latency on each view
- Use Keycloak token introspection endpoint: network call per request, too heavy for a demo
- DRF + TokenAuthentication: explicitly excluded by user constraints

---

## Decision 3: Keycloak Admin API Authentication in D1

**Decision**: Use a Keycloak service account attached to `d1-client` with `realm-management` realm role.

**Mechanism**:
- `d1-client` is a confidential client with service accounts enabled in Keycloak
- Grant `d1-client`'s service account the `realm-management` role (or specific sub-roles: `manage-users`, `query-users`, `manage-realm`)
- `python-keycloak` `KeycloakAdmin` initialized in `kc_admin/client.py` using client credentials from env vars
- `KeycloakAdmin` handles token refresh automatically

**Why service account over admin credentials**:
- Principle of least privilege: service account gets only the `manage-users` sub-roles, not full admin
- Admin credentials are too broad and harder to rotate
- Stored in D1's `.env` — separate from Keycloak admin password

**Alternatives considered**:
- Use Keycloak admin username/password: rejected — overly privileged, poor security hygiene
- Call Admin API directly with `requests`: rejected — reinvents python-keycloak with no benefit

---

## Decision 4: Keycloak Realm Import

**Decision**: Use Keycloak's `--import-realm` startup flag with a JSON export mounted at `/opt/keycloak/data/import/`.

**Mechanism**:
```yaml
# docker-compose.yml (Keycloak service)
command: start-dev --import-realm
volumes:
  - ./keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json
```
- If the realm already exists, Keycloak skips import (idempotent)
- `start-dev` mode: no TLS cert required, embedded HTTP server, development use only
- PostgreSQL configured explicitly via `KC_DB_*` env vars to override the default H2

**Alternatives considered**:
- Manual realm setup via Keycloak admin console: not reproducible, violates US5
- Keycloak initialization script (`kcadm.sh`): more complex than `--import-realm`, requires Keycloak to be running first
- Terraform Keycloak provider: overkill for a single-realm dev setup

---

## Decision 5: PostgreSQL Multi-Database Initialization

**Decision**: Single `postgres/init.sql` mounted at `/docker-entrypoint-initdb.d/init.sql`.

**Content pattern**:
```sql
-- Create users
CREATE USER keycloak_user WITH PASSWORD '${KEYCLOAK_DB_PASSWORD}';
CREATE USER d1_user WITH PASSWORD '${D1_DB_PASSWORD}';
CREATE USER d2_user WITH PASSWORD '${D2_DB_PASSWORD}';

-- Create databases
CREATE DATABASE keycloak_db OWNER keycloak_user;
CREATE DATABASE d1_db OWNER d1_user;
CREATE DATABASE d2_db OWNER d2_user;

-- Restrict access (revoke public schema access)
REVOKE ALL ON DATABASE keycloak_db FROM PUBLIC;
REVOKE ALL ON DATABASE d1_db FROM PUBLIC;
REVOKE ALL ON DATABASE d2_db FROM PUBLIC;
```

**Note**: PostgreSQL's `/docker-entrypoint-initdb.d/` runs only on the first container initialization (when the data volume is empty). Password injection via `--build-arg` is not possible; passwords are passed as env vars to the Postgres container and referenced from the init script via `psql` session variables or the script uses the `POSTGRES_*` env vars.

**Practical approach**: Hard-code placeholder passwords in `init.sql` (from `.env.example`) and document that users must set real passwords via `.env`. The init script runs as the `postgres` superuser; no security issue since this only runs locally.

**Alternatives considered**:
- Separate init files per database: cleaner but adds complexity for a 3-database setup
- Entrypoint shell script: unnecessary when a SQL file is sufficient

---

## Decision 6: Docker Compose Healthcheck Ordering

**Decision**: Use `depends_on` with `condition: service_healthy` for all inter-service dependencies.

**Chain**: `postgres` → `keycloak` → `d1`, `d2`

**Healthcheck implementations**:
- `postgres`: `pg_isready -U postgres`
- `keycloak`: `curl -f http://localhost:8080/health/ready`
- `d1`: `curl -f http://localhost:8000/health/` (simple Django view returning 200)
- `d2`: `curl -f http://localhost:8000/health/`

**Why this matters**: `depends_on` without `condition: service_healthy` only waits for container start, not application readiness. Keycloak takes 20–40 seconds to initialize; D1/D2 must not attempt OIDC discovery before Keycloak's realm is ready.

---

## Decision 7: UserProfile Sync Strategy in D1

**Decision**: `UserProfile` as a `OneToOneField` to Django's built-in `User`. mozilla-django-oidc creates/updates the `User`; the custom backend hook creates/updates the `UserProfile`.

**Why not a custom `AbstractUser`**:
- Would require `AUTH_USER_MODEL` override and all associated migrations complexity
- mozilla-django-oidc works well with the default `User` model
- A separate `UserProfile` is a clean separation of concerns: Django's `User` handles session auth, `UserProfile` holds Keycloak identity attributes

**Sync timing**: Profile is updated on every login (in `update_user()`), ensuring roles and groups stay current. Mid-session Keycloak changes take effect at next login.

**Roles/groups source**: Keycloak JWT claims — `realm_access.roles` and `groups` (requires a custom Keycloak Protocol Mapper to include groups in the token).

---

## Decision 8: Keycloak Container Variant

**Decision**: `start-dev` mode for development. `start` mode (with TLS) for production.

**Rationale**: `start-dev` requires no TLS certificate, uses HTTP, and is the fastest path for local development. The `KEYCLOAK_VERIFY_SSL` env var controls whether Django services verify the Keycloak certificate (set to `false` for local dev).

**Note**: `start-dev` should never be used in production. The `docker-compose.yml` targets development; a separate production compose file or Helm chart would use `start` with proper certs.
