# Research: User Provisioning with Activation Email

**Feature**: [spec.md](spec.md) | **Date**: 2026-06-18

---

## Decision 1: View pattern — Django form vs JS+API

**Decision**: Django form-based `View` (GET renders form, POST processes it, re-renders on error).

**Rationale**: Native Django form handling retains field values on validation error and provides clean inline error messaging without JavaScript. The existing admin_panel.html uses JS+JSON calls for a different purpose (querying Keycloak data on-the-fly). A dedicated creation form benefits from server-side form validation (FR-011) and fits the "standard Django web application" pattern in the constitution.

**Alternatives considered**:
- JS+API approach (like admin_panel.html): Requires new JSON endpoints and custom JS error injection. Adds complexity for no user-facing benefit.
- Django `FormView` CBV: Possible, but `View` with explicit `get()` and `post()` methods is simpler given the need to load roles from Keycloak on GET.

---

## Decision 2: Separate `provision_user` method vs extending `create_user`

**Decision**: Add a new `provision_user(email, username, first_name, last_name)` method to `KeycloakAdminClient`. Do not modify the existing `create_user`.

**Rationale**: `create_user` sets `emailVerified=True` and accepts a password for immediate access. `provision_user` sets `emailVerified=False`, no password, and adds `requiredActions=['UPDATE_PASSWORD', 'UPDATE_PROFILE']`. These are fundamentally different semantics (immediate vs activation-gated). Keeping them separate avoids a flag-controlled method with diverging code paths.

**Alternatives considered**:
- Add `activation_mode=True` flag to `create_user`: Adds conditional complexity to an already-functional method.
- Modify `create_user` to detect empty password: Implicit behavior change; breaks the principle of least surprise.

---

## Decision 3: `send_activation_email` — python-keycloak API

**Decision**: Add `send_activation_email(user_id)` to `KeycloakAdminClient` calling `admin.send_update_account(user_id=user_id, payload=['UPDATE_PASSWORD', 'UPDATE_PROFILE'])`.

**Rationale**: python-keycloak exposes `send_update_account(user_id, payload, ...)` which maps directly to the Keycloak REST endpoint `PUT /admin/realms/{realm}/users/{id}/execute-actions-email`. The `payload` parameter accepts a list of required action strings. This is the correct method for triggering an activation email with required actions, as opposed to `send_verify_email` which only sends an email-verification link.

**Alternatives considered**:
- `send_verify_email`: Only triggers email verification — does not include UPDATE_PASSWORD or UPDATE_PROFILE. Insufficient.
- Direct HTTP call bypassing python-keycloak: Violates constitution rule to reuse existing integration.

---

## Decision 4: Error handling sequence

**Decision**: Treat each step independently after user creation. If a step fails after the user has been created, show a warning and do not rollback.

**Rationale**: Keycloak does not provide a transaction across user creation + group assignment + role assignment + email. Rolling back manually (delete user on failure) introduces a race condition and adds complexity for an unlikely partial-failure case. The spec explicitly states this policy for email failure (FR-012); applying it consistently to group/role failures is the simplest coherent strategy.

**Sequence**:
1. Create user → if `DuplicateUser` (409), abort with inline form error (no user created)
2. Assign each selected group → if any group fails, log warning, continue, show warning on page
3. Assign role (if selected) → if fails, log warning, show warning on page
4. Send activation email → if fails, show warning (user and assignments remain)
5. All succeeded → show success message with email address

**Alternatives considered**:
- Rollback on any failure: Too complex, race-condition-prone, not aligned with spec for email failure.
- Abort-on-first-failure (stop assigning remaining groups): Leaves user in partially-configured state with no warning. Worse outcome.

---

## Decision 5: Group list — static vs dynamic

**Decision**: Group list in the form is static (hardcoded to the 6 known groups). It is NOT fetched from Keycloak at page load.

**Rationale**: Spec explicitly states the group list is `d1:rrhh`, `d1:worker`, `d1:admin`, `d2:viewer`, `d2:editor`, `d2:admin` — a fixed set. Dynamic fetching would add a Keycloak call on every GET request without any benefit. The app-to-group mapping (D1 vs D2) is also a static fact, known at design time.

**Alternatives considered**:
- Dynamic fetch from `list_groups()`: Adds latency and Keycloak dependency on every page load; returns ALL Keycloak groups, which may include system groups not appropriate for this form.

---

## Decision 6: Role list — dynamic

**Decision**: Role dropdown is populated by calling `kc_client.list_assignable_roles()` on each GET request to the provision view.

**Rationale**: Spec states "realm roles available in the identity system" — this is dynamic data. Consistent with how the admin panel already loads roles. Only realm roles are relevant for this form (client roles like `can-login` are not user-assignable from the provision form).

**Note**: The existing `list_assignable_roles()` returns both realm and client roles. The provision view will filter to realm roles only before populating the dropdown.

---

## Decision 7: New URL placement

**Decision**: New URL at `/provision/` registered in `dashboard/urls.py` as `name='provision-user'`.

**Rationale**: The provision view is a user-facing dashboard feature, not an internal API endpoint. It belongs in `dashboard/` alongside other protected views (`/rrhh/`, `/admin/`, etc.). The `kc_admin/` module hosts the underlying Keycloak client methods and JSON API endpoints, not template views.

---

## Files to create or modify

| File | Action | Reason |
|---|---|---|
| `d1/kc_admin/client.py` | Modify | Add `provision_user()` and `send_activation_email()` |
| `d1/dashboard/views.py` | Modify | Add `UserProvisionView` |
| `d1/dashboard/forms.py` | Create | `UserProvisionForm` with static group choices |
| `d1/dashboard/urls.py` | Modify | Add `/provision/` → `UserProvisionView` |
| `d1/dashboard/templates/dashboard/provision_user.html` | Create | Form template with group labels and feedback messages |
| `d1/kc_admin/tests/test_client.py` | Modify | Tests for `provision_user` and `send_activation_email` |
| `d1/dashboard/tests/test_provision_view.py` | Create | View tests: GET, POST success, duplicate, email failure, auth |
