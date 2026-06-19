# Tasks: User Provisioning with Activation Email

**Input**: Design documents from `specs/003-user-provisioning/`

**References**: [spec.md](spec.md) | [plan.md](plan.md) | [data-model.md](data-model.md) | [research.md](research.md) | [quickstart.md](quickstart.md)

## Format: `[ID] [P?] [Story?] Description — file path`

- **[P]**: Can run in parallel (different files, no unresolved dependencies)
- **[Story]**: Which user story this task belongs to (US1 = P1, US2 = P2, US3 = P3)

---

## Phase 1: Setup

**Purpose**: Confirm existing test infrastructure works before adding to it.

- [x] T001 Verify existing `kc_admin` tests pass by running `docker compose exec d1 python -m pytest kc_admin/tests/ -v` from `keycloak-django-sso/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend client methods and form class that ALL user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Add `provision_user(email, username, first_name='', last_name='')` method to `KeycloakAdminClient` in `keycloak-django-sso/d1/kc_admin/client.py` — payload: `enabled=True, emailVerified=False, requiredActions=['UPDATE_PASSWORD','UPDATE_PROFILE']`, no credentials; raises `DuplicateUser` on 409, `KeycloakConnectionError` on other errors
- [x] T003 Add `send_activation_email(user_id)` method to `KeycloakAdminClient` in `keycloak-django-sso/d1/kc_admin/client.py` — calls `admin.send_update_account(user_id=user_id, payload=['UPDATE_PASSWORD','UPDATE_PROFILE'])`; raises `KeycloakConnectionError` on failure
- [x] T004 [P] Create `keycloak-django-sso/d1/dashboard/forms.py` with `UserProvisionForm`: fields `username` (CharField), `email` (EmailField), `first_name` (CharField optional), `last_name` (CharField optional), `groups` (MultipleChoiceField with CheckboxSelectMultiple, required=False), `role` (ChoiceField optional); static `GROUP_CHOICES` constant with 6 groups labeled with D1/D2 app; role choices injected via `__init__(role_choices=None)`

**Checkpoint**: `provision_user`, `send_activation_email`, and `UserProvisionForm` exist and are importable.

---

## Phase 3: User Story 1 — Admin Creates User + Activation Email (Priority: P1) 🎯 MVP

**Goal**: Admin fills form, user is created in Keycloak, email is sent, admin sees confirmation.

**Independent Test**: Admin with `d1:admin` submits form → new user in Keycloak with `emailVerified=false` and required actions → activation email received → new user can log in.

### Implementation for User Story 1

- [x] T005 [US1] Add `UserProvisionView` class to `keycloak-django-sso/d1/dashboard/views.py` — class-based `View` with `LoginRequiredMixin`, decorated with `@method_decorator(require_groups(['d1:admin']), name='dispatch')`; `get()` method loads realm roles from `kc_client.list_assignable_roles()` (filter to `type=='realm'`), instantiates `UserProvisionForm(role_choices=...)`, renders `dashboard/provision_user.html`; import `UserProvisionForm` from `dashboard.forms` and `kc_client` from `kc_admin.views`
- [x] T006 [P] [US1] Register `path('provision/', UserProvisionView.as_view(), name='provision-user')` in `keycloak-django-sso/d1/dashboard/urls.py` and add `UserProvisionView` to the import list
- [x] T007 [P] [US1] Create `keycloak-django-sso/d1/dashboard/templates/dashboard/provision_user.html` extending `dashboard/base.html` — render `{% csrf_token %}`, `{{ form.non_field_errors }}`, all form fields; render group checkboxes in two labeled fieldsets: "D1 Groups" (`d1:rrhh`, `d1:worker`, `d1:admin`) and "D2 Groups" (`d2:viewer`, `d2:editor`, `d2:admin`); submit button labeled "Create User & Send Activation Email"
- [x] T008 [US1] Implement `UserProvisionView.post()` in `keycloak-django-sso/d1/dashboard/views.py` — validate form, call `kc_client.provision_user(...)`, then for each selected group call `kc_client.assign_group(user_id, group)`, then if role selected call `kc_client.assign_realm_role(user_id, role)`, then call `kc_client.send_activation_email(user_id)`; on full success pass `ctx = {'success': True, 'success_email': ..., 'success_username': ..., 'email_sent': True, 'warnings': [], 'form': UserProvisionForm(role_choices=...)}` (fresh form) and render template
- [x] T009 [US1] Update `keycloak-django-sso/d1/dashboard/templates/dashboard/provision_user.html` to render success block when `success` is True — green message showing "User `{{ success_username }}` created. Activation email sent to `{{ success_email }}`." and reset the form below it
- [x] T010 [P] [US1] Add tests to `keycloak-django-sso/d1/kc_admin/tests/test_client.py`: `test_provision_user_success` (mock `create_user` returns UUID, assert correct payload passed), `test_provision_user_duplicate` (mock `create_user` raises `KeycloakPostError(409)`, assert `DuplicateUser` raised), `test_provision_user_connection_error` (mock raises generic Exception, assert `KeycloakConnectionError`), `test_send_activation_email_success` (mock `send_update_account`, assert called with `payload=['UPDATE_PASSWORD','UPDATE_PROFILE']`), `test_send_activation_email_failure` (mock raises Exception, assert `KeycloakConnectionError`)
- [x] T011 [US1] Create `keycloak-django-sso/d1/dashboard/tests/test_provision_view.py` — fixture: `admin_user` (user with `d1:admin` Django group, force-logged-in client); `mock_kc` fixture patches `dashboard.views.kc_client`; tests: `test_get_provision_admin` (200), `test_get_provision_non_admin` (redirect to access-denied), `test_get_provision_unauthenticated` (redirect to OIDC login), `test_post_provision_success` (mock `provision_user`→UUID, `list_assignable_roles`→[], `send_activation_email`→None, `assign_group`→None; assert 200, `success=True`, `email_sent=True` in context)

**Checkpoint**: US1 fully testable — admin can reach `/provision/`, submit the form, and see a success message. New user visible in Keycloak.

---

## Phase 4: User Story 2 — Admin Handles Duplicate User Error (Priority: P2)

**Goal**: When username or email already exists, admin sees an inline form error and all other field values are retained.

**Independent Test**: Submit form with an existing username → form re-renders with error, field values preserved; correct the conflict and resubmit → success.

### Implementation for User Story 2

- [x] T012 [US2] Add `DuplicateUser` exception handling to `UserProvisionView.post()` in `keycloak-django-sso/d1/dashboard/views.py` — catch `DuplicateUser` from `kc_client.provision_user(...)`, call `form.add_error(None, 'A user with this username or email already exists.')`, re-render template with the bound form (field values retained); also catch `KeycloakConnectionError` from `provision_user` with appropriate message
- [x] T013 [P] [US2] Update `keycloak-django-sso/d1/dashboard/templates/dashboard/provision_user.html` to render `{{ form.non_field_errors }}` prominently above the form fields in a red/error-styled block so duplicate errors are clearly visible
- [x] T014 [US2] Add tests to `keycloak-django-sso/d1/dashboard/tests/test_provision_view.py`: `test_post_duplicate_user` (mock `provision_user` raises `DuplicateUser`; assert 200, `form.non_field_errors` non-empty, `success` not in context or False), `test_post_connection_error` (mock `provision_user` raises `KeycloakConnectionError`; assert 200, form error shown)

**Checkpoint**: US2 testable — submitting a duplicate username or email shows a clear inline error and retains form data.

---

## Phase 5: User Story 3 — Email Fails, User Already Created (Priority: P3)

**Goal**: When activation email fails after user creation, admin sees a warning (not an error) and the user account + assignments are preserved.

**Independent Test**: Simulate email failure → admin sees warning, user exists in Keycloak with correct groups/role.

### Implementation for User Story 3

- [x] T015 [US3] Add warning-not-rollback handling to `UserProvisionView.post()` in `keycloak-django-sso/d1/dashboard/views.py` — wrap `assign_group` calls in try/except (catch `GroupNotFound`, `KeycloakConnectionError`); wrap `assign_realm_role` in try/except (catch `RoleNotFound`, `KeycloakConnectionError`); wrap `send_activation_email` in try/except (catch `KeycloakConnectionError`, set `email_sent=False`); collect all warnings in a `warnings` list; always pass `warnings` and `email_sent` to context on success
- [x] T016 [P] [US3] Update `keycloak-django-sso/d1/dashboard/templates/dashboard/provision_user.html` to render a warnings block when `warnings` is non-empty — yellow/warning-styled `<ul>` listing each warning string; displayed below the success message if both are present
- [x] T017 [US3] Add tests to `keycloak-django-sso/d1/dashboard/tests/test_provision_view.py`: `test_post_email_fails` (mock `send_activation_email` raises `KeycloakConnectionError`; assert 200, `email_sent=False`, `warnings` non-empty, `success=True`), `test_post_group_assign_fails` (mock `assign_group` raises `KeycloakConnectionError`; assert 200, `warnings` non-empty, `success=True`), `test_post_role_assign_fails` (mock `assign_realm_role` raises `KeycloakConnectionError`; assert 200, `warnings` non-empty, `success=True`)

**Checkpoint**: US3 testable — email/group/role failures result in a warning message; user account always retained.

---

## Phase 6: Polish & Validation

**Purpose**: End-to-end validation and constitution compliance check.

- [x] T018 [P] Run full test suite for the feature: `docker compose exec d1 python -m pytest kc_admin/tests/ dashboard/tests/test_provision_view.py -v` from `keycloak-django-sso/` and fix any failures
- [x] T019 Manually validate all 5 scenarios from `specs/003-user-provisioning/quickstart.md` against the running stack: happy path, duplicate error, email failure, access control, and group visual labels

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **blocks all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 complete
- **US2 (Phase 4)**: Depends on Phase 3 (builds on the POST handler in `views.py`)
- **US3 (Phase 5)**: Depends on Phase 4 (adds more exception handlers to the same POST handler)
- **Polish (Phase 6)**: Depends on all previous phases

### Within Phase 3

- T005 (view skeleton) → T008 (POST logic) → T011 (view tests) must be sequential
- T006 (urls.py), T007 (template), T010 (client tests) can run in parallel with T005

### Within Phase 4

- T012 (error handling in view) and T013 (template error display) can run in parallel
- T014 (tests) must follow T012

### Within Phase 5

- T015 (warning handling in view) and T016 (template warnings) can run in parallel
- T017 (tests) must follow T015

---

## Parallel Execution Examples

```
# Phase 2 — run simultaneously:
T002 Add provision_user() to client.py
T004 Create forms.py with UserProvisionForm  ← different file, no dependency

# Phase 3 — after T005 starts:
T006 Register URL in urls.py          ← different file
T007 Create provision_user.html       ← different file
T010 Add client tests                 ← different file, different module
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Phase 1: Verify tests
2. Phase 2: Add `provision_user`, `send_activation_email`, `UserProvisionForm`
3. Phase 3: Full US1 implementation — view, URL, template, happy path, tests
4. **STOP**: validate with quickstart Scenario 1 + Scenario 4

### Incremental Delivery

1. **After Phase 3**: Admin can create users and send activation emails
2. **After Phase 4**: Admin sees clear errors on duplicate username/email
3. **After Phase 5**: Admin sees helpful warning when email or assignments partially fail
4. **After Phase 6**: All scenarios validated end-to-end

---

## Notes

- The module-level `kc_client` singleton is imported from `kc_admin.views` — do NOT create a new instance in `dashboard/views.py`
- `list_assignable_roles()` returns both realm and client roles — filter to `type == 'realm'` before passing as role choices to the form
- On form submission success, pass a **fresh** `UserProvisionForm` (not the bound form) to the template context so the form is empty and ready for the next user
- The `GroupNotFound`, `RoleNotFound`, `KeycloakConnectionError`, `DuplicateUser` exceptions are imported from `kc_admin.client`
- Tests use `patch('dashboard.views.kc_client')` following the existing pattern in `kc_admin/tests/test_views.py`
