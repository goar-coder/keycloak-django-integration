# Feature Specification: Group-Based Access Control

**Feature Branch**: `002-group-access-control`

**Created**: 2026-06-17 | **Updated**: 2026-06-18

**Status**: Implemented

**Input**: Add group-based access control to D1 and D2. Keycloak manages application-specific groups (prefixed `d1:*`, `d2:*`, and `admin:*`). Groups are synced to local user records on login. Views enforce group membership using OR logic — at least one matching group grants access. App-level login access is controlled via Keycloak Client Roles and custom Authentication Flows.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — D1 RRHH User Accesses Their Section (P1) ✅

A user in `d1:rrhh` logs into D1 and can access `/home/` and `/rrhh/`. They cannot access `/worker/`, `/data/`, or `/admin/`.

**Acceptance Scenarios**:
1. **Given** `d1:rrhh`, **When** `/rrhh/`, **Then** 200.
2. **Given** `d1:rrhh`, **When** `/worker/`, **Then** access-denied page.
3. **Given** `d1:rrhh`, **When** `/admin/`, **Then** access-denied page.
4. **Given** `d1:rrhh`, **When** `/home/`, **Then** 200.
5. **Given** `d1:rrhh`, **When** `/data/`, **Then** access-denied page.

---

### User Story 2 — D1 Worker User Accesses Their Section (P1) ✅

A user in `d1:worker` can access `/home/` and `/worker/`. Cannot access `/rrhh/`, `/data/`, or `/admin/`.

**Acceptance Scenarios**:
1. **Given** `d1:worker`, **When** `/worker/`, **Then** 200.
2. **Given** `d1:worker`, **When** `/home/`, **Then** 200.
3. **Given** `d1:worker`, **When** `/rrhh/`, **Then** access-denied.
4. **Given** `d1:worker`, **When** `/data/`, **Then** access-denied.
5. **Given** `d1:worker`, **When** `/admin/`, **Then** access-denied.

---

### User Story 3 — D1 Admin Has Full Access (P1) ✅

A user in `d1:admin` can access all D1 routes: `/home/`, `/rrhh/`, `/worker/`, `/data/`, `/admin/`.

**Acceptance Scenarios**:
1. **Given** `d1:admin`, **When** any D1 protected route, **Then** 200.

---

### User Story 4 — D1 Data User Accesses /data/ (P1) ✅

A user in `d1:data` can access `/home/` and `/data/`. Cannot access `/rrhh/`, `/worker/`, or `/admin/`.

**Acceptance Scenarios**:
1. **Given** `d1:data`, **When** `/data/`, **Then** 200.
2. **Given** `d1:data`, **When** `/home/`, **Then** 200.
3. **Given** `d1:data`, **When** `/rrhh/`, **Then** access-denied.
4. **Given** `d1:data`, **When** `/admin/`, **Then** access-denied.

---

### User Story 5 — Cross-App admin:data Group Accesses /data/ in Both Apps (P1) ✅

A user in `admin:data` can access `/data/` in D1 and `/data/` in D2, provided they also have `can-login` for the respective app. The group syncs in both applications (D1 reads `admin:*`, D2 reads `admin:*`).

**Acceptance Scenarios**:
1. **Given** `admin:data` + D1 login, **When** `/data/` in D1, **Then** 200.
2. **Given** `admin:data` + D2 login, **When** `/data/` in D2, **Then** 200.
3. **Given** `admin:data`, **When** `/rrhh/` in D1, **Then** access-denied.

---

### User Story 6 — D2 Report User Sees Reports (P2) ✅

A user in `d2:report` can access `/reports/`. Users with only `d2:viewer` cannot access `/reports/` (viewer group no longer grants reports access).

**Acceptance Scenarios**:
1. **Given** `d2:report`, **When** `/reports/`, **Then** 200.
2. **Given** `d2:viewer` only, **When** `/reports/`, **Then** access-denied.
3. **Given** `d2:report`, **When** `/editor/`, **Then** access-denied.

---

### User Story 7 — D2 Editor Can Write Content (P2) ✅

A user in `d2:editor` can access `/editor/`. Cannot access `/admin/`.

**Acceptance Scenarios**:
1. **Given** `d2:editor`, **When** `/editor/`, **Then** 200.
2. **Given** `d2:editor`, **When** `/admin/`, **Then** access-denied.

---

### User Story 8 — D2 Data User Accesses /data/ (P2) ✅

A user in `d2:data` (or `d2:admin` or `admin:data`) can access `/data/` in D2.

**Acceptance Scenarios**:
1. **Given** `d2:data`, **When** `/data/`, **Then** 200.
2. **Given** `d2:data`, **When** `/reports/`, **Then** access-denied.

---

### User Story 9 — D2 Admin Has Full D2 Access (P2) ✅

A user in `d2:admin` can access all D2 routes.

**Acceptance Scenarios**:
1. **Given** `d2:admin`, **When** any D2 protected route, **Then** 200.

---

### User Story 10 — App-Level Login Control via Keycloak (P1) ✅

A user without the `can-login` client role for D1 cannot complete the Keycloak login flow for D1 — they receive "Invalid username or password" before any Django code is reached. The inverse applies for D2.

**Acceptance Scenarios**:
1. **Given** a user with only `d2-client:can-login`, **When** they attempt to log into D1, **Then** Keycloak denies the login before issuing a token.
2. **Given** a user with `d1-client:can-login`, **When** they log into D1, **Then** login succeeds normally.
3. **Given** `user_admin_data` with both `can-login` roles, **When** logging into either app, **Then** login succeeds.

---

### User Story 11 — Admin Panel: Create User with Password (P2) ✅

An admin using `/admin-panel/` can create a new Keycloak user including setting an initial password. The created user can immediately log in with those credentials.

**Acceptance Scenarios**:
1. **Given** the Create User form, **When** email, username, and password are filled and submitted, **Then** the user is created in Keycloak with the provided password set.
2. **Given** a missing password field, **When** the form is submitted, **Then** a 400 error is returned.

---

### User Story 12 — Admin Panel: Assign Role/Group via Dropdown (P2) ✅

An admin can assign roles and groups to a user using dropdowns populated from Keycloak — no need to type role or group names manually. Roles include realm roles and client roles for both D1 and D2.

**Acceptance Scenarios**:
1. **Given** the Assign Role section, **When** the page loads, **Then** a dropdown lists all assignable roles labeled by type (`[realm]`, `[d1-client]`, `[d2-client]`).
2. **Given** the Assign Group section, **When** the page loads, **Then** a dropdown lists all Keycloak groups alphabetically.
3. **Given** a role selected and user sub provided, **When** Assign Role is submitted, **Then** the role is assigned in Keycloak.

---

### User Story 13 — Authenticated User Without App Group Sees Access Denied (P3) ✅

A user who authenticates successfully but has no group matching the current app sees the access-denied page — never the login page and never a server error.

**Acceptance Scenarios**:
1. **Given** authenticated user with no `d1:*` or `admin:*` groups, **When** any protected D1 page, **Then** access-denied page shown.
2. **Given** the access-denied page, **When** rendered, **Then** it lists the required groups for that route.

---

### User Story 14 — Group Change Takes Effect at Next Login (P3) ✅

An admin changes a user's group in Keycloak. The change is reflected in the application at the user's next login with no manual intervention.

**Acceptance Scenarios**:
1. **Given** user in `d1:worker` only, **When** admin adds `d1:rrhh` and user re-logs in, **Then** `/rrhh/` is accessible.
2. **Given** user in `d1:rrhh`, **When** admin removes them and user re-logs in, **Then** `/rrhh/` shows access-denied.

---

### Edge Cases

- User in multiple groups (e.g., `d1:rrhh` AND `d1:worker`) has access to union of all permitted pages — OR logic.
- User with both `d1:*` and `d2:*` groups: each app ignores the other's prefix.
- `admin:*` groups sync in both D1 and D2 (cross-app group support).
- Empty or missing groups claim → user treated as having no groups.
- A user without `can-login` role is blocked at Keycloak before any token is issued.
- Adding a `d2:viewer` user to a D1 authentication flow that requires `d1-client:can-login` still blocks them.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Groups in Keycloak use naming convention: `d1:rrhh`, `d1:worker`, `d1:data`, `d1:admin` for D1; `d2:viewer`, `d2:editor`, `d2:data`, `d2:report`, `d2:admin` for D2; `admin:data` for cross-app access. Groups are flat — no hierarchy.
- **FR-002**: Keycloak includes group memberships in the JWT via a Group Membership mapper using flat name format (full path disabled).
- **FR-003**: On every login, D1 reads `groups` from the JWT, filters to `d1:*` and `admin:*`, and syncs to `auth.Group`. Previously held groups not present are removed.
- **FR-004**: On every login, D2 reads `groups` from the JWT, filters to `d2:*` and `admin:*`, and syncs to `auth.Group`. Previously held groups not present are removed.
- **FR-005**: D1 enforces group access: `/home/` → `d1:rrhh|d1:worker|d1:data|d1:admin`; `/rrhh/` → `d1:rrhh|d1:admin`; `/worker/` → `d1:worker|d1:admin`; `/data/` → `d1:data|d1:admin|admin:data`; `/admin/` → `d1:admin`.
- **FR-006**: D2 enforces group access: `/reports/` → `d2:report`; `/editor/` → `d2:editor|d2:admin`; `/data/` → `d2:data|d2:admin|admin:data`; `/admin/` → `d2:admin`.
- **FR-007**: Access control uses OR semantics — at least one matching group grants access.
- **FR-008**: An authenticated user lacking required groups sees a dedicated access-denied page, not a login redirect or server error.
- **FR-009**: The access-denied page lists which groups are required for the requested route.
- **FR-010**: Group data reflects the identity provider state at the time of the user's most recent login. Mid-session changes take effect at next login.
- **FR-011**: App-level access is gated by a `can-login` Client Role on each Keycloak client. This is enforced in a custom Keycloak Authentication Flow before token issuance — not in Django backend code.
- **FR-012**: The `require_groups(allowed_groups)` decorator is the single reusable mechanism for group enforcement on all views.
- **FR-013**: The admin panel Create User form MUST include a password field. The password is set in Keycloak at user creation time. No password is stored in Django.
- **FR-014**: The admin panel Assign Role section MUST display a dropdown populated from Keycloak showing all assignable roles (realm roles + client roles for d1-client and d2-client), labeled by type.
- **FR-015**: The admin panel Assign Group section MUST display a dropdown populated from Keycloak showing all groups alphabetically.
- **FR-016**: The realm export MUST include all groups, test user assignments, and service account permissions so the environment is fully reproducible from `docker compose up`.

### Key Entities

- **Application Group**: Named Keycloak group controlling access to a section. Prefixed by app (`d1:`, `d2:`) or cross-app (`admin:`). Flat — no parent/children.
- **Cross-App Group**: A group with `admin:` prefix that syncs in both D1 and D2. Example: `admin:data` grants `/data/` access in both apps.
- **Local Group Record**: The synced copy of a user's group memberships in Django `auth.Group`, filtered by the app's own prefix(es).
- **Access Policy**: Mapping from protected route to required groups (OR logic). Declared once per view via `require_groups` decorator.
- **Access Denied Page**: Shown to authenticated users lacking required groups. Displays which groups are needed.
- **Can-Login Client Role**: A Keycloak client-level role (`can-login`) assigned per user per app. Enforced in Keycloak's auth flow — users without this role cannot log into the corresponding app.

---

## Success Criteria *(mandatory)*

- **SC-001**: 100% of group-protected routes correctly grant/deny access — zero false positives or negatives.
- **SC-002**: Every access-denied response is a rendered page, never a server error or unexpected login redirect.
- **SC-003**: Group changes in Keycloak are reflected after the user's next login — no manual intervention.
- **SC-004**: A user in multiple groups accesses the union of all permitted pages — no unexpected denials.
- **SC-005**: A user without `can-login` for an app is blocked at the Keycloak level — no Django code is reached.
- **SC-006**: `admin:data` users can access `/data/` in both D1 and D2 without being in any `d1:*` or `d2:*` group.
- **SC-007**: A fresh `docker compose up` from the realm export results in all groups, users, and client roles available immediately.
- **SC-008**: Adding a new group-protected route requires only one change — the `require_groups` declaration on the view.
- **SC-009**: Admin panel can create a user with a password; that user can immediately log in. Role and group assignment uses dropdowns — no manual typing of names.

---

## Assumptions

- Users may belong to groups from multiple applications simultaneously. Each app ignores the other's prefixes.
- A user with no matching groups can still authenticate; they simply cannot access any group-protected page.
- The `d2:viewer` group remains in Keycloak but no longer grants access to `/reports/` — it is a legacy group preserved for backward compatibility.
- Group membership sync happens only on login, not on every request.
- `d1:admin` and `d2:admin` are application-level roles only — they do not grant Keycloak admin console access.
- The `can-login` role enforcement uses Keycloak's CONDITIONAL flow type with a negated role condition, blocking token issuance entirely for unauthorized users.
- The admin panel is accessible to any authenticated D1 user; production deployments should add a `d1:admin` group check.
