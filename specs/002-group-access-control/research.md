# Research: Group-Based Access Control

**Date**: 2026-06-17
**Feature**: `002-group-access-control`

## Decision 1: Group Storage — Django `auth.Group` vs. Custom Model

**Decision**: Use Django's built-in `django.contrib.auth.models.Group` as the local group store.

**Rationale**: The `auth_group` and `auth_user_groups` tables are already created by Django's default migrations (`django.contrib.auth` is already in `INSTALLED_APPS` in both D1 and D2). The built-in `user.groups.filter(name__in=...).exists()` is a single indexed query. No new model or migration is needed.

**Alternatives considered**:
- Custom `AppGroup` model: Unnecessary complexity. The built-in Group model handles the N:M user-group relationship and indexed lookups natively.
- Store in session: Mutable mid-session, hard to invalidate, stale group data risk.
- Re-read from `UserProfile.groups` JSONField: JSONField queries are not indexed on PostgreSQL without a GIN index. The `auth_user_groups` join table is already indexed on both `user_id` and `group_id`.

---

## Decision 2: Group Sync Point — Login-time Only

**Decision**: Sync groups to `auth.Group` in `update_user()` (and `create_user()`) of the OIDC backend, called on every successful login.

**Rationale**: `mozilla-django-oidc`'s `OIDCAuthenticationBackend.update_user()` is called on every successful OIDC callback, which is the moment the JWT is freshest. The spec explicitly states mid-session changes take effect at next login.

**Alternatives considered**:
- Middleware that re-reads groups on every request: Would require a Keycloak API call per request, violating the "JWT tokens validated on every request" constitution rule only in the sense of Admin API — the session refresh middleware already handles token freshness. Overhead not justified for this feature.
- Signal on `SessionRefresh`: More complex hook, same outcome.

---

## Decision 3: Group Filter — Prefix Convention

**Decision**: Each app filters the JWT `groups` claim to only its own prefix: D1 reads `d1:*`, D2 reads `d2:*`. Cross-app groups are silently ignored.

**Rationale**: Prevents accidental privilege escalation across apps. A user in `d2:admin` must not gain D1 admin access. The prefix is a cheap string startswith check; no configuration needed.

**Implementation**:
```python
# D1 backend
jwt_groups = [g for g in claims.get('groups', []) if g.startswith('d1:')]
# D2 backend
jwt_groups = [g for g in claims.get('groups', []) if g.startswith('d2:')]
```

**Alternatives considered**:
- Single shared group namespace without prefix: Cross-app group collisions possible. A `viewer` group in D1 and `viewer` in D2 would be the same Django Group, creating unintended access.
- Separate `auth_group` tables via multi-DB routing: Over-engineered. Prefix convention achieves full isolation with minimal code.

---

## Decision 4: `require_groups` Decorator — OR Logic, Wraps `login_required`

**Decision**: `require_groups(allowed_groups)` checks `user.groups.filter(name__in=allowed_groups).exists()`. Returns 200 if any group matches (OR). Redirects to `/access-denied/` (D1) or `/group-denied/` (D2) if no group matches. Redirects to `LOGIN_URL` if not authenticated.

**Rationale**: Mirrors the existing `require_scope` pattern already in `d2/accounts/decorators.py`, which uses the same redirect + functools.wraps pattern. Keeps both decorators consistent. The decorator rather than a mixin is preferred because: (a) function-based views may be added, (b) the `@method_decorator` pattern already established in D2's `ReportsView` works cleanly with class-based views.

**Redirect destination carries context**:
```
/access-denied/?required=d1:rrhh,d1:admin
```
The access-denied view reads the `required` query parameter to display the specific groups needed.

**Alternatives considered**:
- Mixin class `GroupRequiredMixin`: Works, but D2 already uses the decorator pattern. Mixing both patterns would be inconsistent.
- Raise `PermissionDenied` (Django 403): Would render the generic Django 403 page, not the custom access-denied page with group context.

---

## Decision 5: Keycloak Groups — Flat, Prefixed, No Hierarchy

**Decision**: Add 6 top-level Keycloak groups (no subgroups). Names match the prefix convention exactly: `d1:rrhh`, `d1:worker`, `d1:admin`, `d2:viewer`, `d2:editor`, `d2:admin`.

**Rationale**: The group membership mapper on `d1-client` and `d2-client` already sends the `groups` claim with the full group name. Flat groups are simpler to manage and the prefix alone provides all necessary scoping.

**Keycloak groups claim format**: The existing `groups` mapper uses `full.path: false`, so the claim contains `["d1:rrhh", "d1:admin"]` (not `["/d1:rrhh", "/d1:admin"]`). The sync code must match this format.

**Alternatives considered**:
- Keycloak group hierarchy (d1/ → rrhh, worker, admin): Path-based naming would require stripping the path prefix. Adds complexity with no benefit for this flat use case.
- Keycloak roles instead of groups: Roles are already used for `admin`/`viewer` at realm level. Mixing role-based and group-based access control in the same claims would require disambiguating. Keeping them separate is cleaner.

---

## Decision 6: D2 Access Control — Groups AND Scopes Are Complementary

**Decision**: `/reports/` in D2 gets BOTH the existing `require_scope('read:reports')` AND the new `require_groups(['d2:viewer','d2:editor','d2:admin'])`. Both must pass. The scope check runs first (outermost decorator).

**Rationale**: The user's description says "añadir control de acceso basado en grupos" — add, not replace. Keeping both layers demonstrates that D2 can enforce both OAuth2 scope-based and group-based authorization, which is the stated purpose of D2 as a "scope testing app" now extended to group testing.

**Access denied separation**: Group denial redirects to `/group-denied/` while scope denial redirects to `/denied/`. This keeps the two mechanisms independently observable, useful for testing.

**Alternatives considered**:
- Replace scope with groups: Would lose the existing scope-testing capability of D2, which is a core feature of the platform per the constitution.
- Single denial page for both: Merging them would make it harder to diagnose which access control layer fired.

---

## Resolved: Test User Group Assignments

The realm export must assign test users to groups that enable end-to-end testing of all access policies without manual Keycloak configuration:

| User | D1 Groups | D2 Groups | Covers |
|------|-----------|-----------|--------|
| `testadmin` | `d1:admin` | `d2:admin` | Full access to both apps |
| `testuser` | `d1:worker` | `d2:viewer` | Partial access — tests both grant and deny scenarios |

A third test user (e.g., `testguest`) with no groups would allow testing the "authenticated but no group" scenario, but creating one is optional — the same can be achieved by temporarily removing groups from `testuser` in Keycloak admin.
