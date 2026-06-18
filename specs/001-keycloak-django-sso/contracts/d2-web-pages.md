# Contract: D2 Web Pages

**Service**: D2 (scope testing web app)
**Base URL**: `http://localhost:8002` (development)
**Auth mechanism**: Django session set by mozilla-django-oidc
**Scope mechanism**: Scopes stored in `request.session["oidc_scopes"]` at login time

All pages return HTML (Django templates). No JSON API. Auth failures redirect to Keycloak. Scope failures redirect to `/denied/`.

---

## Scope Definitions

| Scope name | Protects route | Description |
|------------|---------------|-------------|
| `read:reports` | `GET /reports/` | Permission to view the reports page |
| `write:data` | `GET /data/` | Permission to view the data-write page |

Scopes are defined as Client Scopes in Keycloak (`app-realm`) and assigned to users via the `d2-client` audience mapper.

---

## Routes

### `GET /`

Home page. Visible to all authenticated users regardless of scopes. Shows the user's email and lists available scope-protected pages with their required scopes.

| Property | Value |
|----------|-------|
| Authentication required | Yes (OIDC session) |
| Scope required | None |
| Response (authenticated) | 200 HTML — user email, scope list, navigation |
| Response (unauthenticated) | 302 → `/oidc/authenticate/?next=/` |

**Template context**:
- `user` — Django `User` object
- `user_scopes` — `list[str]` from session (e.g., `["openid", "read:reports"]`)

---

### `GET /reports/`

Reports page. Requires the `read:reports` scope in the user's access token.

| Property | Value |
|----------|-------|
| Authentication required | Yes (OIDC session) |
| Scope required | `read:reports` |
| Response (scope present) | 200 HTML — reports content |
| Response (scope absent) | 302 → `/denied/?required=read:reports` |
| Response (unauthenticated) | 302 → `/oidc/authenticate/?next=/reports/` |

---

### `GET /data/`

Data-write page. Requires the `write:data` scope in the user's access token.

| Property | Value |
|----------|-------|
| Authentication required | Yes (OIDC session) |
| Scope required | `write:data` |
| Response (scope present) | 200 HTML — data-write content |
| Response (scope absent) | 302 → `/denied/?required=write:data` |
| Response (unauthenticated) | 302 → `/oidc/authenticate/?next=/data/` |

---

### `GET /denied/`

Access Denied page. Displayed when an authenticated user lacks the scope required for the page they tried to access.

| Property | Value |
|----------|-------|
| Authentication required | Yes (OIDC session) |
| Scope required | None |
| Query params | `required` (optional) — the scope name that was missing |
| Response | 200 HTML — "Access Denied" message, required scope displayed, link to `/` |

**Template context**:
- `required_scope` — the scope name from the `required` query param (or generic message if absent)
- `user_scopes` — user's current scopes from session

---

### `GET /oidc/authenticate/`

OIDC login initiation. Handled by mozilla-django-oidc.

| Property | Value |
|----------|-------|
| Authentication required | No |
| Query params | `next` (optional) — post-login redirect |
| Response | 302 → Keycloak authorization URL for `d2-client` |

---

### `GET /oidc/callback/`

OIDC callback. Stores scopes from the access token into the session via `D2OIDCBackend`.

| Property | Value |
|----------|-------|
| Authentication required | No (public callback) |
| Query params | `code`, `state` (from Keycloak) |
| Response (success) | 302 → `next` param or `/` |
| Response (failure) | 302 → `/` with session error message |

**Side effect**: Sets `request.session["oidc_scopes"]` from the decoded access token `scope` claim.

---

### `GET /health/`

Liveness check for Docker Compose healthcheck.

| Property | Value |
|----------|-------|
| Authentication required | No |
| Response | 200 `{"status": "ok"}` (JSON) |

---

### `GET /logout/` or `POST /logout/`

Terminates the OIDC session and redirects to Keycloak logout.

| Property | Value |
|----------|-------|
| Authentication required | Yes (OIDC session) |
| Response | 302 → Keycloak logout URL → `/?logged_out=true` |

---

## Scope Enforcement Implementation Reference

The `@require_scope` decorator (in `d2/accounts/decorators.py`) checks the session:

```python
# Pseudocode — actual implementation in tasks.md
def require_scope(scope_name):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"/oidc/authenticate/?next={request.path}")
            user_scopes = request.session.get("oidc_scopes", [])
            if scope_name not in user_scopes:
                return redirect(f"/denied/?required={scope_name}")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```
