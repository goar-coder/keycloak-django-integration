# Feature Specification: Keycloak-Django SSO Platform

**Feature Branch**: `001-keycloak-django-sso`

**Created**: 2026-06-16
**Last Updated**: 2026-06-17

**Status**: Implemented

**Input**: User description: "Quiero construir un proyecto dockerizado llamado keycloak-django-sso con Keycloak 24, dos Django apps (D1 y D2) y un PostgreSQL compartido"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin Manages Keycloak Users via D1 (Priority: P1)

An administrator authenticates into D1 through Keycloak single sign-on. Once inside, they can create new Keycloak users, assign roles and groups to existing users, retrieve the full user list, and deactivate users — all from the D1 web interface without accessing the Keycloak admin console directly.

**Why this priority**: This is the primary administrative capability of the platform. It delegates Keycloak user management to application-level users without granting them direct Keycloak console access.

**Independent Test**: Log in as an admin user in D1, perform each management action (create, assign role, assign group, list, deactivate) and confirm the changes are reflected in Keycloak's user registry.

**Acceptance Scenarios**:

1. **Given** an authenticated D1 session, **When** the admin submits a create-user request with an email address, **Then** the new user appears in the Keycloak `app-realm` user list with the provided email.
2. **Given** an existing Keycloak user, **When** the admin assigns a realm role via D1, **Then** that role appears in the user's Keycloak profile.
3. **Given** an existing Keycloak user, **When** the admin assigns a group via D1, **Then** the user appears as a member of that group in Keycloak.
4. **Given** an active Keycloak user, **When** the admin deactivates them via D1, **Then** that user can no longer complete the Keycloak login flow.
5. **Given** an authenticated D1 session, **When** the admin requests the user list, **Then** all users in `app-realm` are returned with their current status.

---

### User Story 2 - Regular User Authenticates and Accesses Protected D1 Pages (Priority: P2)

A regular user visits D1, is redirected to Keycloak to log in, and after successful authentication can access all protected pages. Their Keycloak identity — unique identifier, email address, roles, and group memberships — is reflected in their local D1 profile. Logging out terminates both the local D1 session and the shared identity provider session.

**Why this priority**: This is the authentication foundation for all D1 users. No other D1 functionality is accessible without a working single sign-on flow.

**Independent Test**: Log in with a Keycloak user, confirm the redirect flow completes, and verify that protected pages are accessible and the user profile correctly reflects the Keycloak identity data. Then log out and confirm neither D1 nor D2 accepts the session.

**Acceptance Scenarios**:

1. **Given** an unauthenticated user visits a protected D1 page, **When** they arrive, **Then** they are redirected to the Keycloak login screen.
2. **Given** a user completes the Keycloak login, **When** they are redirected back to D1, **Then** they can access protected pages without re-authenticating.
3. **Given** a successfully authenticated D1 session, **When** the user profile is inspected, **Then** it contains the Keycloak subject identifier, email, current roles, and current group memberships from the token.
4. **Given** a logged-in user clicks logout, **When** the logout completes, **Then** both the D1 local session and the Keycloak SSO session are terminated; the user must re-authenticate to access either D1 or D2.
5. **Given** a user whose session has expired, **When** they attempt to access a protected D1 page, **Then** they are redirected to Keycloak to re-authenticate before the page is served.
6. **Given** a user already authenticated in D1, **When** they open D2, **Then** they are automatically recognized without entering credentials again (shared SSO session).

---

### User Story 3 - User With Required Scopes Accesses Protected D2 Pages (Priority: P3)

A user whose Keycloak token contains the required OAuth2 scopes (e.g., `read:reports`, `write:data`) logs into D2 and successfully views the scope-protected pages. Scopes are optional and must be explicitly granted per user in the identity provider before they appear in the token.

**Why this priority**: D2's core purpose is to demonstrate and validate scope-based access control. The success path must work correctly before testing the denial path.

**Independent Test**: In Keycloak, explicitly grant the target scope to a test user for the D2 client. Log in to D2 and verify that the corresponding protected page renders without error or redirect.

**Acceptance Scenarios**:

1. **Given** a user whose token contains `read:reports`, **When** they access the D2 reports page, **Then** the page renders successfully.
2. **Given** a user whose token contains `write:data`, **When** they access the D2 data-write page, **Then** the page renders successfully.
3. **Given** a user logged into D2 with all required scopes, **When** they navigate between scope-protected pages they are authorized for, **Then** each page loads without errors or unexpected redirects.
4. **Given** a user who has not been granted any optional scopes, **When** they log in to D2, **Then** they can access the D2 home page but not any scope-protected pages.

---

### User Story 4 - User Without Required Scopes Is Denied D2 Access (Priority: P4)

A user who is authenticated in D2 but whose token lacks a required scope attempts to access a scope-protected page and receives a clear, informative "Access Denied" page rather than a generic error. The page shows both the required scope and the user's current scopes.

**Why this priority**: Enforcing and visibly communicating scope denial is the validation purpose of D2. Without correct denial behavior, the system cannot be used to test Keycloak scope configuration.

**Independent Test**: Log in to D2 with a user whose token does NOT contain the required scope, attempt to access the protected page, and confirm the access-denied page is shown with the missing scope name.

**Acceptance Scenarios**:

1. **Given** a user without the `read:reports` scope, **When** they attempt to access the D2 reports page, **Then** they see an "Access Denied" page (not a server error and not a blank response) that names the missing scope.
2. **Given** a user with no scopes at all, **When** they attempt to access any scope-protected page, **Then** an "Access Denied" page is shown for each protected resource.
3. **Given** an unauthenticated user who accesses a scope-protected D2 page, **When** the system responds, **Then** they are first redirected to Keycloak login; scope enforcement applies only after authentication succeeds.

---

### User Story 5 - Platform Starts Fully Configured from a Single Command (Priority: P5)

A developer runs a single startup command and the entire platform — identity provider, both web applications, and the shared database — starts in the correct order, initializes all databases, imports the Keycloak realm configuration, and becomes fully operational without any additional manual steps.

**Why this priority**: Reproducible, zero-manual-configuration startup is essential for developer onboarding, local development, and automated testing environments.

**Independent Test**: On a clean environment with Docker installed and a populated `.env` file, run the startup command and confirm all services reach a healthy state and the end-to-end login flow works.

**Acceptance Scenarios**:

1. **Given** a clean environment with Docker and a `.env` file, **When** the startup command runs, **Then** the database service initializes three isolated databases (`keycloak_db`, `d1_db`, `d2_db`), each accessible only by its own dedicated user.
2. **Given** the database service is healthy, **When** the identity provider starts, **Then** the `app-realm` configuration (including both clients, all standard OIDC scopes, custom application scopes, roles, groups, and pre-configured test users) is imported automatically from the committed export file.
3. **Given** the identity provider is healthy, **When** D1 and D2 start, **Then** both run any pending data migrations and then become available to users without manual intervention.
4. **Given** all services are healthy, **When** a user opens D1 or D2 in a browser, **Then** the full login flow works without any configuration step beyond providing the `.env` file.
5. **Given** the platform is running, **When** the database service is restarted, **Then** all services detect the disruption and recover without requiring manual intervention.

---

### Edge Cases

- What happens when a Keycloak user's roles or groups change between D1 sessions? The local profile MUST be re-synchronized on the next successful login.
- How does D1 handle a Keycloak Admin API error during a user management operation? The endpoint MUST return a structured error response; it MUST NOT leave the local state inconsistent.
- What if a user accesses D1 or D2 while the identity provider is temporarily unavailable? The user sees a recoverable error message and can retry once the identity provider is back.
- What if a scope-protected D2 page is accessed by a user whose token has just expired? They are redirected to re-authenticate, not shown an access-denied page.
- What if the Keycloak realm export file is absent or corrupted at startup? The identity provider starts but realm configuration is incomplete; D1 and D2 MUST surface a clear connectivity or configuration error rather than silently failing.
- What if a user logs out of D1 while a D2 tab is still open? The D2 tab will fail to load new pages once the shared identity provider session expires and will redirect to Keycloak login.
- What if a user in D2 has no scopes assigned? They can log in and see the home page, but every scope-protected route shows the Access Denied page with a clear explanation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Both D1 and D2 MUST authenticate users exclusively via the configured identity provider using the OIDC Authorization Code Flow. No local username/password authentication is permitted in either application.
- **FR-002**: Upon each successful D1 login, the system MUST synchronize the user's unique identifier, email address, current roles, and current group memberships from the identity token into a local profile record.
- **FR-003**: Every page in D1 and D2 that requires authentication MUST redirect unauthenticated users to the identity provider login page before granting access.
- **FR-004**: D1 MUST expose an endpoint to create a new user in the identity provider, accepting at minimum an email address and username.
- **FR-005**: D1 MUST expose an endpoint to assign a named role to an existing identity provider user.
- **FR-006**: D1 MUST expose an endpoint to assign an existing identity provider user to a named group.
- **FR-007**: D1 MUST expose an endpoint to list all users registered in the identity provider realm.
- **FR-008**: D1 MUST expose an endpoint to deactivate (disable) an existing identity provider user by their unique identifier.
- **FR-009**: All D1 user management endpoints MUST be protected by an active, valid OIDC session. Unauthenticated or session-expired requests MUST be rejected.
- **FR-010**: D2 MUST enforce scope-based access control: each protected page MUST verify the presence of its required scope in the authenticated user's token before rendering.
- **FR-011**: D2 MUST render an explicit "Access Denied" page when an authenticated user's token lacks a required scope. The page MUST display the name of the missing scope and the user's current scopes.
- **FR-012**: The platform MUST run all services (identity provider, D1, D2, database) as isolated containers orchestrated by a single configuration file.
- **FR-013**: The shared database service MUST be initialized with three isolated logical databases (`keycloak_db`, `d1_db`, `d2_db`), each accessible only by its own dedicated database user with no cross-database permissions.
- **FR-014**: The identity provider realm (`app-realm`) including both application clients (`d1-client`, `d2-client`), all standard OIDC client scopes (`email`, `profile`, `roles`), custom application scopes (`read:reports`, `write:data`), post-logout redirect URIs, roles, groups, and pre-configured test users MUST be imported automatically from a version-controlled export file on every fresh container start.
- **FR-015**: Services MUST start in dependency order enforced by health checks: database service → identity provider → D1 and D2. No service MUST begin its startup sequence until its dependency is healthy.
- **FR-016**: Every credential, secret, client ID, client secret, database URL, and service endpoint MUST be supplied via environment variables. No secret or sensitive value MUST appear in source code or version-controlled files.
- **FR-017**: The identity provider session token MUST be validated on every authenticated request. Expired tokens MUST trigger re-authentication; they MUST NOT be silently accepted.
- **FR-018**: D1 and D2 MUST share the same identity provider SSO session. A user authenticated in one application MUST be automatically recognized in the other without re-entering credentials.
- **FR-019**: Logging out of either D1 or D2 MUST terminate the shared identity provider SSO session, not only the local application session. After logout, the user MUST be required to re-authenticate in all applications.
- **FR-020**: The identity provider MUST be configured with explicit post-logout redirect URIs for each client so that logout flows return users to the correct application entry point.

### Key Entities *(include if feature involves data)*

- **UserProfile (D1-local)**: A local record that mirrors a Keycloak user's identity attributes within D1's database. Fields: unique Keycloak subject identifier (`sub`), `email`, `roles` (list of current role names), `groups` (list of current group names), `last_synced_at` timestamp. Written only during login synchronization; never mutated by local auth.
- **Realm User**: The authoritative user record in the identity provider. Attributes include: unique subject ID, email, first name, last name, enabled/disabled status, realm roles, group memberships. Managed via the identity provider Admin API from D1.
- **OAuth2 Scope**: A named permission token present in a user's access token (e.g., `read:reports`, `write:data`). Defined as optional scopes in the identity provider client. Must be explicitly granted per user; not assigned by default. Evaluated per protected route in D2.
- **Realm Configuration**: The version-controlled JSON export of the `app-realm`, containing client definitions (`d1-client`, `d2-client`), all standard OIDC client scope definitions with their protocol mappers, custom application scopes, post-logout redirect URIs, realm roles, groups, and pre-configured test users. Auto-imported on identity provider startup.
- **Database User**: A PostgreSQL user with access restricted to exactly one logical database (`keycloak_db`, `d1_db`, or `d2_db`). Created by the database initialization script.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer with Docker installed can go from `git clone` to a fully working end-to-end login flow using only a `.env` file and the startup command, in under 5 minutes on a standard development machine.
- **SC-002**: A user can complete the full unauthenticated-to-protected-page flow (initial visit → identity provider login → redirect back → page rendered) in under 5 seconds on a typical network.
- **SC-003**: 100% of protected routes in D1 and D2 redirect unauthenticated users to the identity provider; zero protected routes are accidentally accessible without authentication.
- **SC-004**: 100% of D2 scope-protected routes correctly grant access to users with the required scope and deny access to users without it, with zero false positives and zero false negatives.
- **SC-005**: All five D1 user management operations (create, assign role, assign group, list, deactivate) complete successfully and are verifiable in the identity provider within the same request-response cycle.
- **SC-006**: The platform starts in the correct dependency order on every `docker compose up` without manual intervention. Each service is healthy before its dependents begin initialization.
- **SC-007**: Zero secrets, credentials, or client secrets appear in source code, committed configuration files, or application logs. All sensitive values are externalized to environment variables.
- **SC-008**: Logout from either application terminates the shared identity provider session. After logout, accessing a protected page in either application redirects to the identity provider login screen.

## Assumptions

- Docker and Docker Compose are pre-installed in all development and CI environments.
- A `.env` file (derived from a committed `.env.example`) is the only manual prerequisite before running the startup command; its creation is a documented one-time step.
- The committed realm export file (`keycloak/realm-export.json`) includes all standard OIDC client scope definitions (such as `email`, `profile`, `roles`) in addition to custom application scopes. Importing only custom scopes causes standard login flows to fail.
- The realm export uses development-only default values for client secrets (e.g., `d1-client-dev-secret`). These values are documented in `.env.example` and must be overridden via environment variables in any non-development environment.
- The identity provider must be reachable at two distinct addresses: a public URL accessible from end-user browsers (used for login redirects and logout), and an internal service address used by D1 and D2 for server-to-server calls (token exchange, user info). These addresses differ in containerized environments.
- OAuth2 scopes in D2 (`read:reports`, `write:data`) are configured as optional scopes in the identity provider. They are not assigned to users by default and must be explicitly granted in Keycloak per user or client configuration.
- Two test users are pre-configured in the realm export for immediate validation without manual Keycloak setup: `testadmin` (roles: admin, viewer; group: ops) and `testuser` (role: viewer; group: team-a). Both require pre-set passwords defined in the realm export.
- D1 user management endpoints are intended for administrators; no additional fine-grained role check within D1 is required for v1 (all authenticated D1 sessions may invoke these endpoints).
- D2 is a testing and demonstration application; the scopes `read:reports` and `write:data` serve as representative examples and additional scopes may be added following the same pattern.
- Both D1 and D2 render server-side HTML using the framework's built-in template engine. No client-side JavaScript framework or API-driven frontend is required.
- All inter-service communication occurs over the internal container network. Only the ports necessary for browser access are exposed to the host.
- The PostgreSQL superuser is used only during database initialization; no application service connects as the superuser at runtime.
- User profile synchronization in D1 happens at login time. Mid-session role or group changes in the identity provider take effect at the user's next login.
- The identity provider client configuration must include explicit post-logout redirect URIs. Without them, the identity provider rejects logout requests as invalid redirects.
