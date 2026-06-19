# Feature Specification: User Provisioning with Activation Email

**Feature Branch**: `003-user-provisioning`

**Created**: 2026-06-18

**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Admin Creates a New User and Triggers Activation Email (Priority: P1)

A D1 administrator needs to onboard a new team member. The admin opens the user creation form, fills in the new user's username, email, optional name details, selects the groups that determine which applications the user can access, and optionally assigns a realm role. On submission, the user account is created in the identity system and the new user automatically receives an activation email with a link to set their password and complete their profile. The admin sees a confirmation message.

**Why this priority**: This is the entire value of the feature. All other stories are error paths around this core flow.

**Independent Test**: Can be fully tested by an admin completing the form and verifying (a) the new user appears in the identity system, (b) an activation email is received at the given address, and (c) following the email link allows the new user to log into the appropriate application.

**Acceptance Scenarios**:

1. **Given** an authenticated admin with `d1:admin` group, **When** they submit the creation form with a unique username, a unique email, at least one group, and an optional role, **Then** the user is created in the identity system, the selected groups and role are assigned, and an activation email is sent to the provided address.
2. **Given** the admin just submitted the form successfully, **When** the page loads the result, **Then** a success message is displayed showing the email address where the activation link was sent.
3. **Given** a new user who received the activation email, **When** they click the link and complete their profile and password, **Then** they can log into D1, D2, or both depending on their assigned groups.
4. **Given** the creation form, **When** the admin views the group selection, **Then** each group is clearly labeled to indicate whether it grants access to D1, D2, or both applications.

---

### User Story 2 — Admin Encounters a Duplicate User Error (Priority: P2)

A D1 administrator attempts to create a user but accidentally uses a username or email address already registered. The form must provide a clear, inline error message identifying the conflict so the admin can correct the entry without losing the rest of the form data.

**Why this priority**: Without this, an admin who makes a typo or unknowingly duplicates a user would receive a confusing failure with no recovery path.

**Independent Test**: Can be fully tested by submitting the form with an already-existing username or email and verifying an inline error message appears and the form fields retain their values.

**Acceptance Scenarios**:

1. **Given** the creation form, **When** the admin submits with a username that already exists, **Then** an inline error message identifies the conflict and the form retains all previously entered values.
2. **Given** the creation form, **When** the admin submits with an email address already in use, **Then** an inline error message identifies the conflict and the form retains all previously entered values.
3. **Given** a duplicate error is shown, **When** the admin corrects the conflicting field and resubmits, **Then** the creation proceeds normally.

---

### User Story 3 — Activation Email Fails but User is Already Created (Priority: P3)

An admin creates a new user and the account is successfully created with the correct groups and role, but the activation email cannot be delivered (e.g., email service is misconfigured). The system must not undo the user creation. Instead, it informs the admin of the partial success so they can resend the email or take manual action.

**Why this priority**: This is an edge case in the happy path. The user creation itself succeeds; only the notification step fails. The admin must not be misled into thinking nothing happened.

**Independent Test**: Can be fully tested by simulating an email delivery failure and verifying that the user still exists in the identity system and the admin sees a warning (not an error) distinguishing the partial success.

**Acceptance Scenarios**:

1. **Given** a successful user creation, **When** the activation email cannot be sent, **Then** the user account and all assigned groups and roles remain unchanged, and the admin sees a warning message that clearly distinguishes the email failure from the account creation.
2. **Given** the warning is shown, **When** the admin reads it, **Then** they can identify which user was created and take follow-up action (e.g., manually resend).

---

### Edge Cases

- What happens if the admin submits the form without selecting any groups? → User is created with no group assignments; they can log in only if app-level access allows it, but they cannot access any group-protected routes.
- What happens if group assignment succeeds but role assignment fails? → User is created and groups are assigned; a warning is shown and the user is not deleted.
- What happens if the admin is not in the `d1:admin` group and navigates directly to the creation URL? → They are redirected to the access denied page.
- What happens if the admin submits with both username and email duplicated? → The error message covers both conflicts.
- What happens if the form is submitted empty (missing required fields)? → The form highlights the missing required fields before any creation attempt is made.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The creation form MUST only be accessible to authenticated users who belong to the `d1:admin` group. Unauthenticated users must be redirected to login; authenticated users without `d1:admin` must be redirected to the access denied page.
- **FR-002**: The creation form MUST require `username` and `email` as mandatory fields. `first name` and `last name` are optional.
- **FR-003**: The creation form MUST present group selection as a multi-select list showing all available groups, with a visual label on each group indicating whether it grants access to D1, D2, or both applications.
- **FR-004**: The creation form MUST present role selection as a single-select dropdown populated with realm roles available in the identity system. Role selection is optional.
- **FR-005**: On form submission, the system MUST create the new user in the identity system with the account enabled and email verification pending.
- **FR-006**: On form submission, the system MUST assign all selected groups to the new user.
- **FR-007**: On form submission, if a role was selected, the system MUST assign that role to the new user.
- **FR-008**: On form submission, the system MUST set the new user's required actions to include password setup and profile completion, so that those steps are enforced when the user first logs in.
- **FR-009**: On form submission, the system MUST trigger an activation email to the new user's email address containing a link to complete their account setup.
- **FR-010**: After a fully successful submission, the system MUST display a success message that includes the email address where the activation link was sent.
- **FR-011**: If the submitted `username` or `email` already exists, the system MUST display an inline error on the form identifying the conflict without clearing the other fields.
- **FR-012**: If the activation email fails to send after the user was successfully created, the system MUST display a warning message (not an error) and MUST NOT revert the user creation or any assigned groups or roles.
- **FR-013**: The new user MUST NOT appear in D1's local database until they complete their first login. The form submission creates the user only in the identity system.

### Key Entities

- **Provisional User**: Represents the data entered by the admin before submission. Attributes: `username` (required), `email` (required), `first_name` (optional), `last_name` (optional), `groups` (zero or more, from the available group list), `role` (zero or one realm role). Not persisted in the local database — passed to the identity system on submission.
- **Group Assignment**: A link between a user and an access group. Each group maps exclusively to D1, exclusively to D2, or to both. Determines which application routes the user can access after first login.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An admin can complete the full user creation form and submit it in under 2 minutes from page load to success confirmation.
- **SC-002**: A new user receives the activation email within 30 seconds of the admin submitting the form (assuming email delivery infrastructure is functional).
- **SC-003**: After completing account activation via the email link, the new user can log into the appropriate application(s) on their first attempt without additional admin intervention.
- **SC-004**: 100% of group options in the selection list are visually labeled with the application(s) they grant access to (D1, D2, or both), so that an admin with no prior knowledge can assign groups correctly.
- **SC-005**: When a duplicate username or email is submitted, the admin sees an identifiable inline error message and retains 100% of the other previously entered form values.
- **SC-006**: In the partial-success scenario (user created, email not sent), the admin can distinguish the outcome from a complete failure without reading more than one sentence of feedback.

---

## Assumptions

- Keycloak SMTP configuration is the responsibility of the infrastructure setup, not this feature. If SMTP is not configured, activation emails will not be sent; the feature handles this gracefully (FR-012) but does not configure SMTP.
- Only one realm role can be assigned per user creation session. Multiple roles are out of scope.
- The list of selectable groups is fixed to the six defined groups: `d1:rrhh`, `d1:worker`, `d1:admin` (D1 only), `d2:viewer`, `d2:editor`, `d2:admin` (D2 only). It is not dynamically fetched.
- Realm roles presented in the role dropdown are fetched dynamically from the identity system at page load, consistent with existing behavior in the admin panel.
- The activation email content and appearance are controlled entirely by the identity system (Keycloak). This feature only triggers the send — it does not customize the email template.
- After receiving the activation link, the new user must complete both profile fields (first name, last name) and set a password regardless of whether the admin pre-filled the optional name fields. This is enforced by the identity system, not by D1.
- The feature is added to D1 only. D2 has no user-creation interface.
- Group assignments determine route-level access within applications. App-level login access (whether a user can log into D1 or D2 at all) is controlled by client roles in the identity system, which are outside the scope of this feature.
