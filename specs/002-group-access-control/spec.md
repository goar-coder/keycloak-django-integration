# Feature Specification: Group-Based Access Control

**Feature Branch**: `002-group-access-control`

**Created**: 2026-06-17

**Status**: Draft

**Input**: Add group-based access control to D1 and D2. Keycloak manages application-specific groups (prefixed `d1:*` and `d2:*`). Groups are synced to local user records on login. Views enforce group membership using OR logic — at least one matching group grants access.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - D1 RRHH User Accesses Their Section (Priority: P1)

A user who belongs to the `d1:rrhh` group logs into D1 and can access the RRHH section. They cannot access the Worker section or the Admin section. When they try, they see a clear access-denied page explaining what group they would need.

**Why this priority**: This is the primary authorization use case — demonstrating that authenticated users are still gated by group membership, not just login.

**Independent Test**: Log in to D1 with a user assigned only to `d1:rrhh`. Verify `/rrhh/` loads, and that `/worker/` and `/admin/` show the access-denied page.

**Acceptance Scenarios**:

1. **Given** a user in group `d1:rrhh`, **When** they visit `/rrhh/`, **Then** the page loads successfully.
2. **Given** a user in group `d1:rrhh`, **When** they visit `/worker/`, **Then** they are shown the access-denied page (not a server error, not a login redirect).
3. **Given** a user in group `d1:rrhh`, **When** they visit `/admin/`, **Then** they are shown the access-denied page.
4. **Given** a user in group `d1:rrhh`, **When** they visit `/home/`, **Then** the page loads successfully (home is accessible to all D1 groups).

---

### User Story 2 - D1 Worker User Accesses Their Section (Priority: P1)

A user who belongs to the `d1:worker` group logs into D1 and can access the Worker section and the home page. They cannot access the RRHH section or the Admin section.

**Independent Test**: Log in to D1 with a user assigned only to `d1:worker`. Verify `/worker/` and `/home/` load, and that `/rrhh/` and `/admin/` show the access-denied page.

**Acceptance Scenarios**:

1. **Given** a user in group `d1:worker`, **When** they visit `/worker/`, **Then** the page loads successfully.
2. **Given** a user in group `d1:worker`, **When** they visit `/home/`, **Then** the page loads successfully.
3. **Given** a user in group `d1:worker`, **When** they visit `/rrhh/`, **Then** they are shown the access-denied page.
4. **Given** a user in group `d1:worker`, **When** they visit `/admin/`, **Then** they are shown the access-denied page.

---

### User Story 3 - D1 Admin User Has Full Access (Priority: P1)

A user who belongs to the `d1:admin` group logs into D1 and can access all sections: home, RRHH, Worker, and Admin.

**Independent Test**: Log in to D1 with a user assigned to `d1:admin`. Verify all four pages load successfully.

**Acceptance Scenarios**:

1. **Given** a user in group `d1:admin`, **When** they visit any D1 page (`/home/`, `/rrhh/`, `/worker/`, `/admin/`), **Then** every page loads successfully.

---

### User Story 4 - D2 Viewer Sees Reports (Priority: P2)

A user who belongs to `d2:viewer` logs into D2, can read reports but cannot access the editor or admin areas.

**Independent Test**: Log in to D2 with a user assigned to `d2:viewer`. Verify `/reports/` loads, and `/editor/` and `/admin/` show the access-denied page.

**Acceptance Scenarios**:

1. **Given** a user in group `d2:viewer`, **When** they visit `/reports/`, **Then** the page loads successfully.
2. **Given** a user in group `d2:viewer`, **When** they visit `/editor/`, **Then** they are shown the access-denied page.
3. **Given** a user in group `d2:viewer`, **When** they visit `/admin/`, **Then** they are shown the access-denied page.

---

### User Story 5 - D2 Editor Can Write Content (Priority: P2)

A user who belongs to `d2:editor` logs into D2, can access both reports and the editor area, but not the admin area.

**Independent Test**: Log in to D2 with a user assigned to `d2:editor`. Verify `/reports/` and `/editor/` load, and `/admin/` shows the access-denied page.

**Acceptance Scenarios**:

1. **Given** a user in group `d2:editor`, **When** they visit `/reports/`, **Then** the page loads successfully.
2. **Given** a user in group `d2:editor`, **When** they visit `/editor/`, **Then** the page loads successfully.
3. **Given** a user in group `d2:editor`, **When** they visit `/admin/`, **Then** they are shown the access-denied page.

---

### User Story 6 - D2 Admin Has Full Access (Priority: P2)

A user who belongs to `d2:admin` logs into D2 and can access all areas: reports, editor, and admin.

**Acceptance Scenarios**:

1. **Given** a user in group `d2:admin`, **When** they visit any D2 page (`/reports/`, `/editor/`, `/admin/`), **Then** every page loads successfully.

---

### User Story 7 - Authenticated User Without Any App Group Sees Access Denied (Priority: P3)

A user who is authenticated via Keycloak but has no group membership in the current application's groups (neither `d1:*` nor `d2:*` as applicable) sees the access-denied page for every protected route. They are not redirected to login.

**Independent Test**: Log in with a user who has no `d1:*` groups in D1. Attempt to visit any protected page. Confirm the access-denied page appears (not the Keycloak login screen).

**Acceptance Scenarios**:

1. **Given** an authenticated user with no `d1:*` groups, **When** they visit any group-restricted D1 page, **Then** the access-denied page is shown, not the login page.
2. **Given** an authenticated user with no `d2:*` groups, **When** they visit any group-restricted D2 page, **Then** the access-denied page is shown, not the login page.
3. **Given** the access-denied page, **When** it is shown, **Then** it clearly communicates which group(s) are required for that page.

---

### User Story 8 - Group Change in Identity Provider Takes Effect at Next Login (Priority: P3)

An administrator changes a user's group membership in the identity provider. The change takes effect in D1 and D2 at the user's next login, without requiring any application restart or manual data update.

**Independent Test**: Assign a new group to a user in Keycloak. Have the user log out and log back in. Verify the new group is reflected and access to the newly permitted page is granted.

**Acceptance Scenarios**:

1. **Given** a user currently in only `d1:worker`, **When** an admin adds them to `d1:rrhh` in the identity provider and the user logs out and back in, **Then** they can now access `/rrhh/` without any other intervention.
2. **Given** a user currently in `d1:rrhh`, **When** an admin removes them from that group and the user re-logs in, **Then** they can no longer access `/rrhh/`.

---

### Edge Cases

- What if a user belongs to multiple D1 groups (e.g., `d1:rrhh` AND `d1:worker`)? They should have access to any page that permits either group — OR logic applies.
- What if a user has both `d1:*` and `d2:*` groups? Each application only reads its own prefix — D1 ignores `d2:*` groups and vice versa.
- What if an authenticated user visits an unauthenticated-only page (e.g., home page) but has no groups? They should still see any page that does not require group membership.
- What if the identity provider sends an empty or missing groups claim? The application treats the user as having no groups — all group-protected pages show access denied.
- What if a group-protected page is accessed before the user's session has loaded group data? The page must wait for the group data to be available and not grant access optimistically.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The identity provider MUST define application-specific groups using a naming convention: `d1:rrhh`, `d1:worker`, `d1:admin` for D1; `d2:viewer`, `d2:editor`, `d2:admin` for D2. Groups are flat — no hierarchy or inheritance between them.
- **FR-002**: The identity provider MUST include a user's group memberships in the identity token so that applications can read them on login. The claim must contain all groups across all applications, using the flat list format.
- **FR-003**: On every successful login, D1 MUST read the groups claim from the identity token, filter to only `d1:*` groups, and synchronize them to the user's local group record. Previously held groups not present in the current token MUST be removed.
- **FR-004**: On every successful login, D2 MUST read the groups claim from the identity token, filter to only `d2:*` groups, and synchronize them to the user's local group record. Previously held groups not present in the current token MUST be removed.
- **FR-005**: D1 MUST enforce group-based access control on the following routes: `/home/` requires any of (`d1:rrhh`, `d1:worker`, `d1:admin`); `/rrhh/` requires any of (`d1:rrhh`, `d1:admin`); `/worker/` requires any of (`d1:worker`, `d1:admin`); `/admin/` requires `d1:admin`.
- **FR-006**: D2 MUST enforce group-based access control on the following routes: `/reports/` requires any of (`d2:viewer`, `d2:editor`, `d2:admin`); `/editor/` requires any of (`d2:editor`, `d2:admin`); `/admin/` requires `d2:admin`.
- **FR-007**: Access control logic MUST use OR semantics: a user who holds **at least one** of the required groups for a route is granted access.
- **FR-008**: An authenticated user who lacks the required group for a route MUST be shown a dedicated access-denied page. They MUST NOT be redirected to the login page, nor receive a generic server error.
- **FR-009**: The access-denied page MUST clearly communicate to the user which group or groups are required to access the requested page.
- **FR-010**: Group membership data in each application MUST always reflect the state of the identity provider at the time of the user's most recent login. Mid-session changes in the identity provider take effect at next login.
- **FR-011**: The identity provider realm configuration export MUST include all six application groups and the group membership protocol mapper configuration for both clients, so the setup is fully reproducible from a fresh container start.
- **FR-012**: The group-based access control mechanism MUST be reusable across views in a consistent way: a single protection declaration per view specifies the required groups; the enforcement logic is not duplicated per view.

### Key Entities

- **Application Group**: A named group in the identity provider that controls access to a section of one application. Named with a prefix that identifies the target application (`d1:` or `d2:`). Flat — no parent, no children. Assigned to users in the identity provider.
- **Local Group Record**: The synchronized copy of a user's application-specific group memberships, stored locally per application. Populated from the identity token on every login. Always a subset of the full group list filtered by the application's own prefix.
- **Access Policy**: The mapping between a protected route and the set of groups required to access it (any one of which is sufficient). Declared once per route; enforced centrally.
- **Access Denied Page**: A user-facing page shown when an authenticated user lacks the required group for a route. Displays the required groups for the current page.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of group-protected routes in D1 and D2 correctly grant access to users with a matching group and deny access to users without any matching group — zero false positives and zero false negatives.
- **SC-002**: Every access-denied response is a rendered page with a human-readable explanation, never a generic error page or an unexpected login redirect.
- **SC-003**: Group membership changes made in the identity provider are fully reflected in application behavior after the user's next login — zero manual interventions required.
- **SC-004**: A user who belongs to multiple groups (e.g., `d1:rrhh` and `d1:worker`) has access to the union of all pages those groups permit — no group combination creates unexpected denial.
- **SC-005**: A fresh `docker compose up` from the updated realm export results in all six groups and both mapper configurations being available immediately, without any manual Keycloak setup.
- **SC-006**: Adding a new group-protected route requires specifying only the route and its required groups in one place — the protection logic itself does not need to be re-implemented.

## Assumptions

- The existing authentication flow (OIDC login/logout) and the existing groups claim mapper already deliver group names in the JWT token. This feature adds enforcement logic on top of data already available.
- Users may belong to groups from multiple applications simultaneously (e.g., a user could have both `d1:admin` and `d2:viewer`). Each application silently ignores the other application's groups.
- A user with no groups at all can still log in; they simply cannot access any group-protected page. There is no "default group" assigned on login.
- The six groups defined here are the complete set for v1. Adding a new group in the future follows the same naming convention and requires only identity provider configuration plus a new access policy entry.
- The access-denied page is a static HTML page within each application and does not require identity provider interaction to render.
- Group membership sync happens only on login, not on every request. If an admin removes a user from a group while the user has an active session, the user retains access until their next login.
- The `d1:admin` and `d2:admin` groups are not the same as the Keycloak realm administrator role. They grant application-level admin access within D1 and D2 respectively; they do not grant access to the Keycloak admin console.
- The realm export update is a full replacement of the existing `realm-export.json`. A `docker compose down -v && docker compose up` is required to apply the new group definitions to a running environment.
