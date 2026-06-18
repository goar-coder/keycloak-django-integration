# Data Model: Keycloak-Django SSO Platform

**Feature**: `001-keycloak-django-sso`
**Date**: 2026-06-16

---

## D1 — Main Web App

### Django `User` (built-in `django.contrib.auth.User`)

Managed automatically by `mozilla-django-oidc`. D1 never sets a password.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `id` | AutoField | Django | Internal PK |
| `username` | CharField (unique) | Keycloak `sub` | UUID from Keycloak |
| `email` | EmailField | OIDC `email` claim | Synced at login |
| `is_active` | BooleanField | `True` | Deactivation managed in Keycloak, not here |
| `password` | CharField | `set_unusable_password()` | Never a real password |

**Constraint**: `AUTHENTICATION_BACKENDS = ['accounts.backends.KeycloakOIDCBackend']` — Django's `ModelBackend` is removed.

---

### `UserProfile` (D1: `accounts` app)

Created and updated by `KeycloakOIDCBackend.create_user()` / `update_user()` on every successful login.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | AutoField | PK | Internal |
| `user` | OneToOneField(`User`) | CASCADE, `related_name='profile'` | Linked Django auth user |
| `sub` | CharField(255) | unique, not null | Keycloak user UUID (`sub` claim) |
| `email` | EmailField | blank=True | Keycloak email (denormalized for quick access) |
| `roles` | JSONField | default=list | List of realm role names, e.g. `["admin", "viewer"]` |
| `groups` | JSONField | default=list | List of group names, e.g. `["team-a", "ops"]` |
| `last_synced_at` | DateTimeField | auto_now=True | Timestamp of last Keycloak sync |

**Source of `roles`**: `token_payload["realm_access"]["roles"]` (filtered to exclude Keycloak system roles)
**Source of `groups`**: `token_payload["groups"]` (requires `groups` Keycloak Protocol Mapper enabled for `d1-client`)

**Validation rules**:
- `sub` must match `user.username`
- `roles` and `groups` are overwritten (not merged) on every login to reflect current Keycloak state

**State transitions**:
```
OIDC login → create_user() called (first time) → UserProfile created
OIDC login → update_user() called (subsequent) → roles/groups/email updated
User disabled in Keycloak → next login rejected at Keycloak; UserProfile unchanged
```

---

## D2 — Scope Testing Web App

### No persistent models

D2 has no custom database models. Its database (`d2_db`) is used only for Django's built-in tables (`django_session`, `auth_user`, etc.).

### Session State (D2: `accounts` app)

Scopes are stored in the Django session at login time by `D2OIDCBackend`.

| Session Key | Type | Description |
|-------------|------|-------------|
| `oidc_scopes` | `list[str]` | Parsed scopes from access token, e.g. `["openid", "read:reports", "write:data"]` |
| `oidc_access_token` | `str` | Raw access token (stored by `OIDC_STORE_ACCESS_TOKEN = True`) |

**Scope extraction**:
```
access_token["scope"] → "openid read:reports write:data"
split(" ") → ["openid", "read:reports", "write:data"]
store in session["oidc_scopes"]
```

**Scope check at view time**:
```
@require_scope("read:reports")
def reports_view(request):
    ...
```
Decorator checks `request.session.get("oidc_scopes", [])`. If scope absent → `redirect("/denied/")`.

---

## Keycloak Domain Model (reference — not in Django)

These entities live in Keycloak's `app-realm`, not in any Django database. Documented here for D1 Admin API contract alignment.

### Realm User

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Keycloak user UUID (`sub`) |
| `username` | String | Username in Keycloak |
| `email` | String | User email |
| `enabled` | Boolean | Active/inactive status |
| `realmRoles` | `list[str]` | Realm-level roles assigned |
| `groups` | `list[str]` | Group paths the user belongs to |
| `credentials` | — | Managed by Keycloak; never exposed to Django |

### Realm Role

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Keycloak role UUID |
| `name` | String | Role name (e.g., `admin`, `viewer`) |
| `composite` | Boolean | Whether role bundles sub-roles |

### Group

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Keycloak group UUID |
| `name` | String | Group name (e.g., `team-a`, `ops`) |
| `path` | String | Full path (e.g., `/team-a`) |

### Client Scope

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Keycloak scope UUID |
| `name` | String | Scope name (e.g., `read:reports`, `write:data`) |
| `protocol` | String | Always `openid-connect` |

---

## Database Layout

| Database | Django App | Models Stored |
|----------|-----------|---------------|
| `d1_db` | D1 | `auth_user`, `accounts_userprofile`, Django session & admin tables |
| `d2_db` | D2 | `auth_user`, `django_session`, Django admin tables (no custom models) |
| `keycloak_db` | Keycloak | All Keycloak internal tables (managed by Keycloak, not Django) |

---

## Entity Relationship (D1)

```
auth_user (1) ──── (1) accounts_userprofile
    │                        │
    │                     .sub ──────────→ Keycloak Realm User.id
    │                     .roles ─────────→ Keycloak Realm Role.name[]
    │                     .groups ────────→ Keycloak Group.name[]
    │
    └── django_session (session-based auth via OIDC)
```
