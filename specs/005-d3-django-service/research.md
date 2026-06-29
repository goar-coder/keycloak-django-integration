# Research: D3 Django Service

**Feature**: D3 Django Service  
**Date**: 2026-06-26  
**Status**: Complete — all questions resolved  

---

## §1 Authentication Flow Decision

**Decision**: D3 uses the same Keycloak authentication flow as D1 — combined username+password form (`auth-username-password-form`), NOT the identity-first flow used by D2.

**Rationale**: The spec explicitly states "el flujo de autenticacion tiene la misma logica que el de d1". D1 uses `auth-username-password-form` (combined), which is the standard Keycloak browser form. D2 uses identity-first (`auth-username-form`) because it needs to identify the user before branching to password vs. magic-link. D3 has no such branching requirement, so the simpler combined form is correct.

**Alternatives considered**:
- Identity-first (D2 pattern): Rejected — only needed when the first step is to show different auth options per user.
- Social login/IdP redirect: Out of scope.

---

## §2 Can-Login Role Check Placement

**Decision**: The `can-login` role check is a CONDITIONAL subflow at **prio=1 at the TOP LEVEL** of the D3 Browser Flow (same pattern as D1), NOT inside `d3-client-forms` (which is the D2 pattern).

**Rationale**: In D1, the role check is at the top level because by the time the subflow executes, the user has already been identified (auth completed inside `d3-client-forms` or its equivalent). The `conditional-user-role` evaluator requires a known user, so it must run AFTER the auth forms have completed identification. Placing it at prio=1 (after prio=0 which contains the auth methods) ensures:
1. Auth forms (prio=0) run first → user is identified
2. Role check (prio=1) runs second → user is known, role check can fire

D2's placement inside the forms is necessary because D2's `d2-client-forms` contains the identity step as its FIRST sub-authenticator (`auth-username-form` at prio=0 within the forms flow). D3 uses the combined form and doesn't have this two-phase structure.

**Key detail**: The CONDITIONAL subflow uses `d3-client-role-cfg` authenticatorConfig with:
- `condUserRole`: `d3-client.can-login`
- `negate`: `true`
- This means: IF user does NOT have `can-login` → execute the subflow → `deny-access-authenticator` fires

---

## §3 Group Sync Strategy

**Decision**: D3 syncs Keycloak groups with prefix `d3:` to Django groups. Groups are synced at every login (not lazily on demand).

**Rationale**: Same pattern as D1, which filters `d1:` and `admin:` groups. D3 has no `admin:` groups — only `d3:normas`, `d3:documentos`, `d3:leyes`. The backend (`D3KeycloakOIDCBackend.update_user()`) reads the `groups` claim from the ID token (configured via Keycloak client scope `groups`) and filters for `d3:` prefix.

**Security note**: Groups are refreshed on every successful OIDC login. `SessionRefresh` middleware re-validates the OIDC session on each request (triggering `update_user` on renewal), so group revocations propagate without requiring explicit re-login beyond the renewal cycle.

**Alternatives considered**:
- Sync on every request via Admin API: Rejected — unnecessary performance overhead, violates "no Admin API" constraint.
- Store groups in JWT claims only (no Django groups): Rejected — `require_groups` decorator checks `request.user.groups`, which requires Django group membership.

---

## §4 Keycloak Client Configuration

**Decision**: `d3-client` is a confidential client with:
- Protocol: `openid-connect`
- Access type: `confidential`
- Standard Flow (Authorization Code) enabled
- Direct Access Grants: DISABLED (security best practice)
- Valid redirect URIs: `http://localhost:8003/oidc/callback/*`
- Web origins: `http://localhost:8003`
- Post logout redirect URIs: `http://localhost:8003/`
- Authentication flow: `D3 Browser Flow` (custom, overrides default browser flow)

**Client secret**: Must be a literal value in `realm-export.json` (not `**********`). Keycloak regenerates secrets when the export contains `**********`. The literal value matches `D3_OIDC_CLIENT_SECRET` in `.env`.

**Alternatives considered**:
- Public client: Rejected — confidential client required for server-side OIDC with client_secret.

---

## §5 Keycloak Groups Claim

**Decision**: Groups are exposed to D3 via a Keycloak client scope named `groups` that maps the user's group memberships to the `groups` claim in the ID token/access token.

**Rationale**: This is the same mechanism D1 uses. The `groups` mapper in Keycloak sends full paths (e.g., `/d3:normas`) or simple names (e.g., `d3:normas`) depending on configuration. D1's `update_user()` uses `group.strip('/')` to normalize paths, so `D3KeycloakOIDCBackend` will do the same.

**Key**: The `groups` client scope must be assigned to `d3-client` (either default or optional scope). Without it, the `groups` claim will not appear in the token.

---

## §6 Database Isolation

**Decision**: D3 gets its own PostgreSQL database `d3_db` owned by `d3_user`. The `d3_user` has no access to `d1_db` or `d2_db`. This is enforced at the PostgreSQL GRANT level via `postgres/init.sql`.

**Rationale**: Service isolation requirement (FR-009 + constitution). The init.sql pattern follows D1 and D2 exactly.

---

## §7 No Keycloak Admin API

**Decision**: D3 does NOT use the Keycloak Admin API. It does not create, update, or delete users. It is read-only with respect to Keycloak.

**Rationale**: The spec states explicitly: "No se requiere gestión de usuarios desde D3 (a diferencia de D1, que puede crear usuarios vía Admin API)." Therefore `python-keycloak` is not in `requirements.txt`.

---

## §8 Port and Service Registration

**Decision**: D3 listens on port `8003` (host) mapped to `8000` (container). The service name in `docker-compose.yml` is `d3`. Health check URL is `/health/`.

**Rationale**: Follows D1 (8001) and D2 (8002) port conventions. The `healthcheck` in Docker Compose uses `curl -f http://localhost:8000/health/` inside the container.

---

## §9 Session Configuration

**Decision**: D3 uses default Django session configuration. No special `SESSION_COOKIE_AGE` override (unlike D2 which sets 8 hours for magic link use case).

**Rationale**: The spec says "La sesión de D3 no tiene requisitos de duración especiales más allá de los valores por defecto del realm." Django default session age is 2 weeks (`SESSION_COOKIE_AGE = 1209600`). Keycloak SSO session max (typically 10 hours) will be the effective constraint via `SessionRefresh`.

---

## §10 Template Strategy

**Decision**: Templates are minimal HTML with inline styles — no external CSS framework dependency. Same approach as D1.

**Rationale**: D3's routes serve informational/static content. Template complexity is out of scope. A base template + per-page extension is sufficient.
