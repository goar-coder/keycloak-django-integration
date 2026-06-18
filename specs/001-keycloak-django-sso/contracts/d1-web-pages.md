# Contract: D1 Web Pages

**Service**: D1 (main web app)
**Base URL**: `http://localhost:8001` (development)
**Auth mechanism**: Django session set by mozilla-django-oidc

All pages return HTML (Django templates). No JSON. Auth failures redirect to Keycloak login.

---

## Routes

### `GET /`

Landing page. Renders a welcome message with a login link for unauthenticated users; redirects to `/dashboard/` for authenticated users.

| Property | Value |
|----------|-------|
| Authentication required | No |
| Response (unauthenticated) | 200 HTML — welcome + login button |
| Response (authenticated) | 302 → `/dashboard/` |

---

### `GET /dashboard/`

Main dashboard showing the authenticated user's profile summary.

| Property | Value |
|----------|-------|
| Authentication required | Yes (OIDC session) |
| Response (authenticated) | 200 HTML — user email, roles, groups |
| Response (unauthenticated) | 302 → `/oidc/authenticate/?next=/dashboard/` |

**Template context**:
- `user` — Django `User` object
- `profile` — linked `UserProfile` (sub, email, roles, groups, last_synced_at)

---

### `GET /profile/`

Detailed view of the user's synchronized Keycloak identity.

| Property | Value |
|----------|-------|
| Authentication required | Yes (OIDC session) |
| Response (authenticated) | 200 HTML — sub, email, roles list, groups list, last synced |
| Response (unauthenticated) | 302 → `/oidc/authenticate/?next=/profile/` |

---

### `GET /admin-panel/`

Entry page for Keycloak user management. Renders links to the JSON admin API operations.

| Property | Value |
|----------|-------|
| Authentication required | Yes (OIDC session) |
| Response (authenticated) | 200 HTML — user management interface |
| Response (unauthenticated) | 302 → `/oidc/authenticate/?next=/admin-panel/` |

---

### `GET /oidc/authenticate/`

OIDC login initiation. Handled by mozilla-django-oidc. Redirects the user to Keycloak's authorization endpoint.

| Property | Value |
|----------|-------|
| Authentication required | No |
| Query params | `next` (optional) — redirect target after login |
| Response | 302 → Keycloak authorization URL |

---

### `GET /oidc/callback/`

OIDC callback. Handled by mozilla-django-oidc. Receives the authorization code from Keycloak, exchanges it for tokens, creates/updates Django session and `UserProfile`.

| Property | Value |
|----------|-------|
| Authentication required | No (public callback) |
| Query params | `code`, `state` (from Keycloak) |
| Response (success) | 302 → `next` param or `/dashboard/` |
| Response (failure) | 302 → `/` with session error message |

---

### `GET /health/`

Liveness check for Docker Compose healthcheck. Returns 200 if Django is up.

| Property | Value |
|----------|-------|
| Authentication required | No |
| Response | 200 `{"status": "ok"}` (JSON) |

---

### `GET /logout/` or `POST /logout/`

Terminates the Django OIDC session and redirects to Keycloak's logout endpoint.

| Property | Value |
|----------|-------|
| Authentication required | Yes (OIDC session) |
| Response | 302 → Keycloak logout URL → `/?logged_out=true` |
