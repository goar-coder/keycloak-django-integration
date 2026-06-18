# Quickstart Validation Guide: Keycloak-Django SSO Platform

**Feature**: `001-keycloak-django-sso`
**Created**: 2026-06-16
**Last Updated**: 2026-06-17

This guide describes how to validate that the platform works end-to-end after implementation. It covers setup, startup, and verification of each user story.

---

## Prerequisites

- Docker Engine 24+ and Docker Compose V2 installed
- Port availability: **5433** (PostgreSQL host port), 8080 (Keycloak), 8001 (D1), 8002 (D2)
- Git repository cloned locally

> **Note**: PostgreSQL is exposed on host port **5433** (not 5432) to avoid conflicts with local PostgreSQL installations. The container still uses 5432 internally.

---

## Setup (one-time)

1. Copy the example environment file and fill in the values:

```bash
cp .env.example .env
# Edit .env — set passwords, client secrets, Django SECRET_KEY values
```

Key variables to configure (see `.env.example` for full list):

| Variable | Description |
|----------|-------------|
| `POSTGRES_PASSWORD` | PostgreSQL superuser password |
| `KEYCLOAK_DB_PASSWORD` | Password for `keycloak_user` |
| `D1_DB_PASSWORD` | Password for `d1_user` |
| `D2_DB_PASSWORD` | Password for `d2_user` |
| `KEYCLOAK_ADMIN_PASSWORD` | Keycloak admin console password |
| `KEYCLOAK_SERVER_URL` | Internal Docker network URL for server-to-server calls (default: `http://keycloak:8080`) |
| `KEYCLOAK_PUBLIC_URL` | Public URL for browser-facing redirects (default: `http://localhost:8080`) |
| `D1_OIDC_CLIENT_SECRET` | `d1-client` secret (dev default: `d1-client-dev-secret`) |
| `D1_KC_SERVICE_ACCOUNT_CLIENT_SECRET` | Same as above, used for D1 Admin API calls |
| `D2_OIDC_CLIENT_SECRET` | `d2-client` secret (dev default: `d2-client-dev-secret`) |
| `D1_SECRET_KEY` | Django secret key for D1 |
| `D2_SECRET_KEY` | Django secret key for D2 |

> **Important — two Keycloak URL variables**: `KEYCLOAK_SERVER_URL` is used by D1/D2 for server-to-server calls (token exchange, userinfo) and points to the internal Docker hostname (`http://keycloak:8080`). `KEYCLOAK_PUBLIC_URL` is used for browser-facing redirects (login, logout) and must be reachable from the user's browser (`http://localhost:8080`). If `KEYCLOAK_PUBLIC_URL` is wrong or missing, browser login and logout redirects will fail.

---

## Startup

```bash
docker compose up --build
```

**Expected startup order and healthy signals**:

| Step | What happens | Expected log / indicator |
|------|-------------|--------------------------|
| 1 | `postgres` starts | `database system is ready to accept connections` |
| 2 | `postgres` init | `init.sql` runs: 3 databases + 3 users created |
| 3 | `keycloak` starts (waits for postgres healthy) | `Keycloak 24.0.x … started` |
| 4 | `keycloak` imports realm | `Importing realm from file /opt/keycloak/data/import/realm-export.json` |
| 5 | `d1` starts (waits for keycloak healthy) | gunicorn startup log; migrations run automatically |
| 6 | `d2` starts (waits for keycloak healthy) | Same as D1 |

D1 and D2 run `migrate` automatically before starting the application server — no manual migration step needed.

All 4 services should reach `healthy` status within ~90–120 seconds. Verify:

```bash
docker compose ps
# All services show: Status = Up (healthy)
```

---

## Pre-configured Test Users

The realm export includes two test users — no Keycloak setup required:

| Username | Password | Roles | Group |
|----------|----------|-------|-------|
| `testadmin` | `testadmin123` | `admin`, `viewer` | `ops` |
| `testuser` | `testuser123` | `viewer` | `team-a` |

> Neither user has D2 optional scopes (`read:reports`, `write:data`) assigned by default.
> Assign them manually in Keycloak admin to test VS8.

---

## Validation Scenarios

### VS1 — Platform boots cleanly (US5)

```bash
docker compose ps
```

Expected: All 4 services show `(healthy)`.

```bash
# Confirm 3 databases exist
docker compose exec postgres psql -U postgres -c "\l" | grep -E "keycloak_db|d1_db|d2_db"
```

Expected: 3 rows returned.

```bash
# Confirm Keycloak realm exists and issuer is the public URL
curl -s http://localhost:8080/realms/app-realm/.well-known/openid-configuration | python3 -m json.tool | grep issuer
```

Expected: `"issuer": "http://localhost:8080/realms/app-realm"`

---

### VS2 — D1 unauthenticated redirect (US2, FR-003)

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/dashboard/
```

Expected: `302`

```bash
curl -s -D - http://localhost:8001/dashboard/ | grep Location
```

Expected: `Location: http://localhost:8001/oidc/authenticate/?next=/dashboard/`

---

### VS3 — D1 full login flow (US2)

1. Open `http://localhost:8001/` in a browser
2. Click the login button → browser redirects to Keycloak at `http://localhost:8080`
3. Log in with `testuser / testuser123`
4. After login, browser redirects back to `http://localhost:8001/dashboard/`
5. Dashboard shows the user's email, roles, and groups

**Verify UserProfile sync**:
```bash
docker compose exec d1 python manage.py shell -c "
from accounts.models import UserProfile
p = UserProfile.objects.first()
print(p.sub, p.email, p.roles, p.groups, p.last_synced_at)
"
```

Expected: User's Keycloak UUID, email, `['viewer']`, `['/team-a']`, and a recent timestamp.

---

### VS4 — D1 Admin API: list users (US1, FR-007)

```bash
# With a valid session cookie (copy from browser dev tools after login)
curl -s -H "Cookie: sessionid=<your-session-id>" \
     http://localhost:8001/api/users/ | python3 -m json.tool
```

Expected:
```json
{
  "users": [
    {"id": "...", "username": "testadmin", "email": "testadmin@example.com", "enabled": true, "roles": ["admin", "viewer"], "groups": ["/ops"]},
    {"id": "...", "username": "testuser",  "email": "testuser@example.com",  "enabled": true, "roles": ["viewer"],          "groups": ["/team-a"]}
  ]
}
```

---

### VS5 — D1 Admin API: create user (US1, FR-004)

```bash
curl -s -X POST \
     -H "Cookie: sessionid=<your-session-id>" \
     -H "Content-Type: application/json" \
     -d '{"email": "testcreate@example.com", "username": "testcreate"}' \
     http://localhost:8001/api/users/create/ | python3 -m json.tool
```

Expected: `201` response with `{"id": "...", "email": "testcreate@example.com", "username": "testcreate"}`

Verify in Keycloak admin: `http://localhost:8080/admin` → `app-realm` → Users → `testcreate` should appear.

---

### VS6 — D1 Admin API: assign role (US1, FR-005)

```bash
curl -s -X POST \
     -H "Cookie: sessionid=<your-session-id>" \
     -H "Content-Type: application/json" \
     -d '{"role_name": "viewer"}' \
     http://localhost:8001/api/users/<sub>/roles/assign/ | python3 -m json.tool
```

Expected: `200` with `{"success": true, "user_id": "<sub>", "role": "viewer"}`

---

### VS7 — D1 Admin API: deactivate user (US1, FR-008)

```bash
curl -s -X POST \
     -H "Cookie: sessionid=<your-session-id>" \
     http://localhost:8001/api/users/<sub>/deactivate/ | python3 -m json.tool
```

Expected: `200` with `{"success": true, "user_id": "<sub>", "enabled": false}`

Verify: the deactivated user cannot log in — Keycloak login shows "Account is disabled."

---

### VS8 — D2 scope granted access (US3, FR-010)

**Setup — grant the scope in Keycloak first**:
1. Open `http://localhost:8080/admin` → `app-realm` → Users → `testuser` → Client Scopes tab
2. In the Optional Client Scopes section for `d2-client`, assign `read:reports`

**Test**:
1. Log in to D2 at `http://localhost:8002/` with `testuser / testuser123`
2. Navigate to `http://localhost:8002/reports/`

Expected: Reports page renders (200 HTML).

---

### VS9 — D2 scope denied access (US4, FR-011)

1. Log in to D2 with a user who has **not** been granted `read:reports` (default state for both test users)
2. Navigate to `http://localhost:8002/reports/`

Expected: Browser is redirected to `http://localhost:8002/denied/?required=read:reports`
The denied page shows: "Access Denied — You need the `read:reports` scope to view this page."

---

### VS10 — SSO cross-app auto-login (US2, FR-018)

1. Log in to D1 at `http://localhost:8001/`
2. In the **same browser**, open `http://localhost:8002/` (D2)

Expected: D2 auto-authenticates without showing the Keycloak login screen. The user is already recognized via the shared Keycloak SSO session.

---

### VS11 — Logout terminates SSO session (US2, FR-019)

1. Log in to D1 at `http://localhost:8001/`
2. Confirm D2 also auto-logs in (see VS10)
3. In D1, click Logout

Expected sequence:
- Browser redirects to Keycloak logout endpoint (with `id_token_hint`)
- Keycloak terminates the SSO session
- Browser returns to `http://localhost:8001/` (home page, logged out)

**Verify session terminated**:
4. Open `http://localhost:8001/dashboard/` → redirected to Keycloak login (not auto-logged in)
5. Open `http://localhost:8002/` → redirected to Keycloak login (SSO session gone)

---

### VS12 — Secret hygiene (FR-016, SC-007)

```bash
# Confirm no production secrets in application source code
grep -rn "changeme\|admin123\|d1_pass\|d2_pass" \
  keycloak-django-sso/d1/ keycloak-django-sso/d2/ \
  --include="*.py" --include="*.yml" --include="*.yaml"
```

Expected: No lines found.

```bash
# Confirm .env is gitignored
grep ".env" keycloak-django-sso/.gitignore
```

Expected: `.env` appears in `.gitignore`.

> **Note**: `keycloak/realm-export.json` intentionally contains development-only client secret defaults (`d1-client-dev-secret`, `d2-client-dev-secret`). These are documented in `.env.example` and must be overridden in any non-development environment.

---

## Database Access from Host (e.g., DBeaver)

PostgreSQL is exposed on **host port 5433**:

| Field | Value |
|-------|-------|
| Host | `localhost` |
| Port | `5433` |
| Database | `d1_db` or `d2_db` or `keycloak_db` |
| User | `d1_user` / `d2_user` / `keycloak_user` |
| Password | from `.env` (`D1_DB_PASSWORD`, `D2_DB_PASSWORD`, `KEYCLOAK_DB_PASSWORD`) |

---

## Cleanup

```bash
docker compose down -v   # removes containers AND volumes (full reset, re-imports realm on next up)
docker compose down      # removes containers, keeps volumes (data preserved)
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| D1/D2 won't start | Keycloak not healthy yet | Wait 90–120s; check `docker compose logs keycloak` |
| Browser redirected to `http://keycloak:8080/...` | `KEYCLOAK_PUBLIC_URL` not set | Set `KEYCLOAK_PUBLIC_URL=http://localhost:8080` in `.env` and restart |
| Login fails with "Invalid redirect uri" | Missing redirect URI in Keycloak client | Verify `d1-client` redirect URIs include `http://localhost:8001/oidc/callback/` in Keycloak admin |
| Logout fails with "Invalid redirect uri" | Missing post-logout URI in Keycloak client | Verify `d1-client` attributes contain `post.logout.redirect.uris = http://localhost:8001/` in Keycloak admin |
| Logout doesn't clear Keycloak session | `id_token_hint` not sent | Ensure `OIDC_STORE_ID_TOKEN = True` is in D1/D2 settings; rebuild containers |
| "Update Account Information" shown after login | Test user missing firstName/lastName | User profile is incomplete; update in Keycloak admin or do `docker compose down -v && up --build` to reimport test users |
| Scope not in token | Scope not explicitly granted to user for d2-client | Keycloak admin → Users → [user] → Client Scopes → assign `read:reports` as optional scope for `d2-client` |
| Groups not syncing to UserProfile | Missing `groups` mapper on d1-client | Check `d1-client` → Protocol Mappers → verify the `groups` group membership mapper exists |
| Admin API 401/502 from D1 | D1 cannot reach Keycloak Admin API | Check `KEYCLOAK_SERVER_URL` and `D1_KC_SERVICE_ACCOUNT_CLIENT_SECRET` in `.env` |
| Database connection refused from host | Port conflict or wrong port | Use port `5433` (not 5432) to connect from the host machine |
| "Invalid scopes: openid email" on login | realm-export.json missing built-in OIDC scopes | Full reset: `docker compose down -v && docker compose up --build` |
