# Feature Specification: D2 Split Authentication

**Feature Branch**: `004-d2-split-auth`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Añadir autenticación diferenciada a D2 — flujo bifurcado según rol de usuario: contraseña para `login_form`, magic link de un solo uso para `auto_login`. Sesión absoluta de 8 horas. Sin impacto en D1.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Password Authentication for Form Users (Priority: P1)

A D2 user assigned the `login_form` role accesses the application without an active session. They are redirected to the identity provider where they first enter their username or email. After being identified, the system presents a password prompt. Upon successful authentication they are granted access to D2.

**Why this priority**: This is the simpler of the two authentication paths and validates the core routing mechanism — that the system correctly identifies the user and selects the right flow before the more complex magic-link path is built.

**Independent Test**: Assign a test user the `login_form` role. Navigate to D2 without a session. Enter the username. Verify a password prompt appears (not an email notification screen). Enter a valid password. Verify D2 access is granted.

**Acceptance Scenarios**:

1. **Given** a user with `login_form` role and no active D2 session, **When** they navigate to any protected D2 page, **Then** they are redirected to the identity provider login screen showing only a username/email field.
2. **Given** the user has entered their username/email, **When** the identity provider checks their assigned role, **Then** the user is presented with a password prompt.
3. **Given** the user enters the correct password, **When** they submit, **Then** they are redirected back to D2 with a fully active session.
4. **Given** the user enters an incorrect password, **When** they submit, **Then** they see an authentication error and remain on the login page; no session is created.

---

### User Story 2 - Magic Link Authentication for Auto-Login Users (Priority: P2)

A D2 user assigned the `auto_login` role accesses the application without an active session. They are redirected to the same identity provider screen and enter their username or email. Instead of a password prompt, the system sends a one-time login link to their registered email address and shows an informational screen. When the user clicks the link within one hour, they are authenticated and redirected to D2 — without entering any password.

**Why this priority**: This is the differentiating, higher-value flow for the user segment that should not manage passwords. It depends on the routing mechanism from P1 being established first, and it introduces an external dependency (email delivery + identity provider extension).

**Independent Test**: Assign a test user the `auto_login` role. Navigate to D2 without a session. Enter the username. Verify the informational screen appears (no password prompt). Check the sandbox email inbox and verify a magic link email was received. Click the link. Verify D2 access is granted with no password entered.

**Acceptance Scenarios**:

1. **Given** a user with `auto_login` role and no active D2 session, **When** they navigate to any protected D2 page, **Then** they are redirected to the identity provider login screen showing only a username/email field.
2. **Given** the user has entered their username/email, **When** the identity provider determines their role is `auto_login`, **Then** no password prompt appears and instead an informational screen is shown confirming an email has been sent.
3. **Given** the user is identified as `auto_login`, **When** the system processes the request, **Then** a one-time login link is delivered to their registered email within 30 seconds.
4. **Given** the user receives the email and clicks the link within 1 hour, **When** the link has not been used before, **Then** they are redirected to D2 with a fully active session.
5. **Given** a magic link that has already been clicked once, **When** a user tries to use it again, **Then** they see an error message and are prompted to start the authentication flow again.
6. **Given** a magic link that was generated more than 1 hour ago, **When** the user clicks it, **Then** they see an expiration error and are prompted to start the authentication flow again.

---

### User Story 3 - Absolute 8-Hour Session Expiration (Priority: P3)

Regardless of user activity, all D2 sessions expire exactly 8 hours after the moment of login. When the session expires, the user's next request redirects them to the full authentication flow from step 1 (username entry). This applies equally to both `login_form` and `auto_login` users.

**Why this priority**: Session duration is a security constraint. It does not block US1 or US2 in MVP but must be validated before the feature can be considered production-ready.

**Independent Test**: Log in to D2 with a `login_form` user. Simulate 8 hours elapsed (or configure a short test window). Verify that the next page request redirects to the identity provider login, not to any D2 page.

**Acceptance Scenarios**:

1. **Given** an authenticated D2 user, **When** 8 hours have elapsed since their login, **Then** the next page request redirects them to the identity provider to re-authenticate.
2. **Given** an authenticated user who has been active for 7 hours and 59 minutes, **When** they navigate within D2, **Then** their session is still valid and they remain authenticated.
3. **Given** a session that has just expired, **When** the user completes re-authentication, **Then** a fresh 8-hour session begins from the moment of the new login.
4. **Given** an expired session, **When** evaluated by the system, **Then** expiration is calculated from the login timestamp, not from the timestamp of the last activity.

---

### Edge Cases

- What happens when a user has neither `login_form` nor `auto_login` role? They should see an access-denied message and not be granted a session.
- What happens if the magic link email cannot be delivered (e.g., inbox full)? The user sees the informational screen but the link never arrives; they must start the flow again.
- What if a user with `auto_login` role clicks a magic link from a different browser or device than where they initiated the flow? The link is valid regardless of the originating browser. This case required a transport-layer fix in D2's OIDC callback (see `research.md §7`); from the user's perspective the experience is seamless.
- What if the same `auto_login` user initiates the flow multiple times before clicking any link? Only the most recently generated link is valid; earlier links are invalidated.
- What if a D1 user also exists as a D2 user? Their roles and authentication flows in D1 are completely independent and unaffected.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The first step of D2 authentication MUST display a single input field for username or email, with no password field visible at this stage.
- **FR-002**: After the user submits their username/email, the system MUST check their assigned role and route them to the appropriate authentication flow without further user input.
- **FR-003**: Users with the `login_form` role MUST be presented with a password prompt immediately after username identification.
- **FR-004**: Users with the `auto_login` role MUST NOT be presented with a password prompt at any point in the authentication flow.
- **FR-005**: Upon identifying a user with `auto_login` role, the system MUST send a one-time login link to the user's registered email address automatically.
- **FR-006**: Magic links MUST expire after exactly 1 hour from the moment of generation.
- **FR-007**: Each magic link MUST be invalidated immediately after first use; subsequent click attempts MUST display an error.
- **FR-008**: An informational screen MUST be shown to `auto_login` users after identification, confirming that an email has been sent and providing clear guidance on next steps.
- **FR-009**: Authenticated D2 sessions MUST expire exactly 8 hours after the moment of login, regardless of user activity.
- **FR-010**: Upon session expiration, the user MUST be redirected to the beginning of the D2 authentication flow (step 1: username/email entry).
- **FR-011**: The authentication configuration changes MUST be isolated to the D2 client in the identity provider and MUST NOT affect D1 or any other client.
- **FR-012**: Users without either `login_form` or `auto_login` role MUST be denied access and shown a clear error.

### Key Entities

- **Authentication Flow**: The branching decision at the identity provider after username identification. Determined exclusively by the user's assigned role. Each user has exactly one of two possible flows.
- **Magic Link**: A single-use URL sent to the user's registered email. Contains a time-limited credential. Valid for 1 hour from generation; invalidated on first click. Does not require the user to be on the same browser or device where the flow was initiated.
- **D2 Session**: An authenticated context created at the moment of successful login in D2. Has an absolute lifetime of 8 hours measured from login time. Shared across browser tabs for the same user but scoped exclusively to D2.
- **User Role Assignment**: Each D2 user is pre-assigned exactly one role — `login_form` or `auto_login`. This assignment determines their authentication path and is managed in the identity provider, not in D2.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of users with `login_form` role are shown a password prompt after username entry — zero cases receive the magic link flow.
- **SC-002**: 100% of users with `auto_login` role receive a magic link email within 30 seconds of entering their username — zero cases are shown a password prompt.
- **SC-003**: 100% of magic links are rejected after their first use; 100% of links older than 1 hour are rejected.
- **SC-004**: 100% of D2 sessions terminate within 8 hours of login; zero sessions remain valid beyond the 8-hour window.
- **SC-005**: Zero changes to D1 behavior — D1 users complete authentication via the same flow as before with no visible difference.
- **SC-006**: An `auto_login` user completes the full flow (username entry → email received → link clicked → D2 access) in under 2 minutes under normal email delivery conditions.
- **SC-007**: An `auto_login` user attempting to reuse a spent magic link sees a clear error message within 3 seconds of clicking.

---

## Assumptions

- All D2 users have a valid, deliverable email address registered in the identity provider. No flows are required for users without a registered email.
- Each D2 user is assigned exactly one role (`login_form` or `auto_login`) before first login. No user has both roles simultaneously; no user has neither role (edge case: no-role users receive an error, not a fallback flow).
- The email delivery infrastructure is already configured and operational for the identity provider. The sandbox SMTP server is sufficient for development and testing.
- D2's existing backchannel logout implementation requires no modification.
- The authentication flow differentiation occurs entirely within the identity provider; D2 receives a standard OIDC token regardless of which flow was used. However, the magic-link flow required a minor Django-side addition: a custom OIDC callback view (`MagicLinkCallbackView`) that handles the case where the magic link is opened in a different browser context than where the flow was initiated. This is a transport-layer fix, not an application-logic change — D2 still has no awareness of which authentication path was used.
- The magic link redirects the user to D2 at the standard OIDC callback URL (`http://localhost:8002/oidc/callback/`).
- Isolation between D1 and D2 is enforced at the identity provider client level (`d1-client` vs `d2-client`); no cross-client configuration changes are made.
- The identity provider must be extended with a third-party magic link plugin, as this capability is not available natively. This is a prerequisite for US2.
