# Implementation Plan: User Provisioning with Activation Email

**Branch**: `003-user-provisioning` | **Date**: 2026-06-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-user-provisioning/spec.md`

---

## Summary

Add a dedicated `/provision/` view to D1 that allows `d1:admin` users to create new Keycloak users and trigger an activation email. The view reuses `KeycloakAdminClient` (adding two new methods: `provision_user` and `send_activation_email`), handles duplicate-user errors with inline form feedback, and shows a warning instead of rolling back when email delivery fails. No new database tables — the new user only appears in D1's local DB on their first OIDC login.

---

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Django 5.x, python-keycloak (existing `KeycloakAdminClient`), mozilla-django-oidc

**Storage**: No schema changes. New Keycloak user is created via Admin REST API. D1's `d1_db` unchanged until new user's first login.

**Testing**: pytest + Django test client. Mocking pattern: `patch('dashboard.views.kc_client')` for view tests; `patch` on `KeycloakAdmin` methods for client tests.

**Target Platform**: Linux Docker container (`manage.py runserver` in development, volume-mounted)

**Project Type**: Django web application — views, templates, forms, URLs. No DRF.

**Performance Goals**: Standard Django page load. Keycloak Admin API calls are synchronous server-side (provision creates ≤4 sequential calls: create + assign groups + assign role + send email).

**Constraints**: Must never store a password. Must reuse `kc_client` singleton from `kc_admin/views.py`. Group list is static; role list is fetched dynamically from Keycloak on GET.

**Scale/Scope**: Admin-only feature. Low traffic. No pagination or bulk operations needed.

---

## Constitution Check

| Rule | Status | Notes |
|---|---|---|
| NEVER store passwords in Django | ✅ Pass | `provision_user` sends no credentials; no password field in form |
| Auth 100% Keycloak | ✅ Pass | New user activates via Keycloak email link |
| NEVER commit secrets | ✅ Pass | No new secrets introduced |
| JWT tokens validated on every request | ✅ Pass | `LoginRequiredMixin` + `SessionRefresh` middleware already enforces this |
| All views require login | ✅ Pass | `UserProvisionView` uses `LoginRequiredMixin` + `require_groups(['d1:admin'])` |
| Every view must have at least one test | ✅ Required | `dashboard/tests/test_provision_view.py` tracked in tasks |
| No DRF | ✅ Pass | New view is a standard Django `View` with template rendering |
| No hardcoded credentials | ✅ Pass | No new settings values needed |

---

## Project Structure

### Documentation (this feature)

```text
specs/003-user-provisioning/
├── plan.md              ← this file
├── research.md          ← Phase 0
├── data-model.md        ← Phase 1
├── quickstart.md        ← Phase 1
└── tasks.md             ← Phase 2 (/speckit-tasks)
```

### Source Code Changes

```text
keycloak-django-sso/d1/
├── kc_admin/
│   ├── client.py                           ← ADD: provision_user(), send_activation_email()
│   └── tests/
│       └── test_client.py                  ← ADD: tests for new methods
├── dashboard/
│   ├── views.py                            ← ADD: UserProvisionView
│   ├── forms.py                            ← CREATE: UserProvisionForm
│   ├── urls.py                             ← ADD: path('provision/', ...)
│   └── templates/dashboard/
│       └── provision_user.html             ← CREATE: form template
└── dashboard/tests/
    └── test_provision_view.py              ← CREATE: view tests
```

---

## Implementation Phases

### Phase A — `KeycloakAdminClient` new methods

**File**: `d1/kc_admin/client.py`

#### `provision_user(email, username, first_name='', last_name='') → str`

Creates a Keycloak user configured for activation-email flow:
- `enabled: True`, `emailVerified: False`
- `requiredActions: ['UPDATE_PASSWORD', 'UPDATE_PROFILE']`
- No credentials (no password)
- Returns the new user's Keycloak UUID
- Raises `DuplicateUser` on 409
- Raises `KeycloakConnectionError` on other errors

```python
def provision_user(self, email: str, username: str, first_name: str = '', last_name: str = '') -> str:
    start = time.monotonic()
    payload = {
        'email': email,
        'username': username,
        'firstName': first_name,
        'lastName': last_name,
        'enabled': True,
        'emailVerified': False,
        'requiredActions': ['UPDATE_PASSWORD', 'UPDATE_PROFILE'],
    }
    try:
        user_id = self._get_admin().create_user(payload)
        self._log('kc_provision_user', username=username, id=user_id, duration_ms=int((time.monotonic() - start) * 1000))
        return user_id
    except KeycloakPostError as exc:
        if exc.response_code == 409:
            raise DuplicateUser(username) from exc
        raise KeycloakConnectionError(str(exc)) from exc
    except Exception as exc:
        raise KeycloakConnectionError(str(exc)) from exc
```

#### `send_activation_email(user_id) → None`

Triggers `execute-actions-email` for `UPDATE_PASSWORD` and `UPDATE_PROFILE`:

```python
def send_activation_email(self, user_id: str) -> None:
    start = time.monotonic()
    try:
        self._get_admin().send_update_account(
            user_id=user_id,
            payload=['UPDATE_PASSWORD', 'UPDATE_PROFILE'],
        )
        self._log('kc_send_activation_email', user_id=user_id, duration_ms=int((time.monotonic() - start) * 1000))
    except Exception as exc:
        logger.error('action=kc_send_activation_email_error user_id=%s error=%s', user_id, exc)
        raise KeycloakConnectionError(str(exc)) from exc
```

---

### Phase B — `UserProvisionForm`

**File**: `d1/dashboard/forms.py` (new file)

A standard Django `Form` with:
- `username`: `CharField(max_length=150)`
- `email`: `EmailField()`
- `first_name`: `CharField(max_length=150, required=False)`
- `last_name`: `CharField(max_length=150, required=False)`
- `groups`: `MultipleChoiceField(choices=GROUP_CHOICES, required=False, widget=CheckboxSelectMultiple)`
- `role`: `ChoiceField(required=False)` — choices injected at instantiation from Keycloak

`GROUP_CHOICES` is a module-level constant (static):
```python
GROUP_CHOICES = [
    ('d1:rrhh',   'D1 — RRHH'),
    ('d1:worker', 'D1 — Worker'),
    ('d1:admin',  'D1 — Admin'),
    ('d2:viewer', 'D2 — Viewer'),
    ('d2:editor', 'D2 — Editor'),
    ('d2:admin',  'D2 — Admin'),
]
```

Role choices are passed in via the constructor:
```python
def __init__(self, *args, role_choices=None, **kwargs):
    super().__init__(*args, **kwargs)
    if role_choices:
        self.fields['role'].choices = [('', '— No role —')] + role_choices
```

---

### Phase C — `UserProvisionView`

**File**: `d1/dashboard/views.py`

Class-based `View` with `LoginRequiredMixin` + `require_groups(['d1:admin'])` decorator.

```python
@method_decorator(require_groups(['d1:admin']), name='dispatch')
class UserProvisionView(LoginRequiredMixin, View):
    template_name = 'dashboard/provision_user.html'

    def _get_role_choices(self):
        try:
            roles = kc_client.list_assignable_roles()
            return [(r['name'], r['name']) for r in roles if r['type'] == 'realm']
        except KeycloakConnectionError:
            return []

    def get(self, request):
        role_choices = self._get_role_choices()
        form = UserProvisionForm(role_choices=role_choices)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        role_choices = self._get_role_choices()
        form = UserProvisionForm(request.POST, role_choices=role_choices)
        ctx = {'form': form}

        if not form.is_valid():
            return render(request, self.template_name, ctx)

        data = form.cleaned_data
        warnings = []

        # Step 1: Create user
        try:
            user_id = kc_client.provision_user(
                email=data['email'],
                username=data['username'],
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
            )
        except DuplicateUser:
            form.add_error(None, 'A user with this username or email already exists in Keycloak.')
            return render(request, self.template_name, ctx)
        except KeycloakConnectionError:
            form.add_error(None, 'Unable to reach identity provider. Please try again.')
            return render(request, self.template_name, ctx)

        # Step 2: Assign groups
        for group_name in data.get('groups', []):
            try:
                kc_client.assign_group(user_id, group_name)
            except (GroupNotFound, KeycloakConnectionError) as exc:
                warnings.append(f'Could not assign group "{group_name}": {exc}')

        # Step 3: Assign role (if selected)
        if data.get('role'):
            try:
                kc_client.assign_realm_role(user_id, data['role'])
            except (RoleNotFound, KeycloakConnectionError) as exc:
                warnings.append(f'Could not assign role "{data["role"]}": {exc}')

        # Step 4: Send activation email
        email_sent = True
        try:
            kc_client.send_activation_email(user_id)
        except KeycloakConnectionError:
            email_sent = False
            warnings.append('Activation email could not be sent. The user was created — resend manually from Keycloak.')

        ctx.update({
            'success': True,
            'success_email': data['email'],
            'success_username': data['username'],
            'email_sent': email_sent,
            'warnings': warnings,
            'form': UserProvisionForm(role_choices=role_choices),  # fresh form on success
        })
        return render(request, self.template_name, ctx)
```

The module-level `kc_client` from `kc_admin.views` is **imported directly** (not reinstantiated):
```python
from kc_admin.views import kc_client
```

---

### Phase D — URL

**File**: `d1/dashboard/urls.py`

Add:
```python
path('provision/', UserProvisionView.as_view(), name='provision-user'),
```

---

### Phase E — Template

**File**: `d1/dashboard/templates/dashboard/provision_user.html`

Structure:
- Extends `dashboard/base.html`
- Success block: shown when `success=True` — green box with email address, note about activation email
- Warning block: shown when `warnings` is non-empty — yellow box listing each warning
- Form block: `<form method="POST">`
  - `{% csrf_token %}`
  - `{{ form.non_field_errors }}` (for duplicate/connection errors)
  - Fields: username, email, first_name, last_name
  - Group checkboxes: rendered in two labeled sections — "D1 groups" and "D2 groups" — using `form.groups`
  - Role dropdown: `form.role`
  - Submit button: "Create User & Send Activation Email"
- On success, form is reset (fresh empty form rendered below or instead of old form)

---

### Phase F — Tests

#### `d1/kc_admin/tests/test_client.py` additions

- `test_provision_user_success`: mock `create_user` returns UUID → assert payload has `emailVerified=False`, `requiredActions` set, no credentials
- `test_provision_user_duplicate`: mock `create_user` raises `KeycloakPostError(409)` → assert `DuplicateUser` raised
- `test_provision_user_connection_error`: mock raises generic exception → assert `KeycloakConnectionError` raised
- `test_send_activation_email_success`: mock `send_update_account` → assert called with correct payload
- `test_send_activation_email_failure`: mock `send_update_account` raises exception → assert `KeycloakConnectionError` raised

#### `d1/dashboard/tests/test_provision_view.py` (new file)

- `test_provision_get_admin`: GET by `d1:admin` user → 200
- `test_provision_get_non_admin`: GET by non-admin user → redirect to access-denied
- `test_provision_get_unauthenticated`: GET without session → redirect to OIDC
- `test_provision_post_success`: POST with valid data, all mocks succeed → 200 with `success=True`, `email_sent=True`
- `test_provision_post_duplicate`: POST → mock `provision_user` raises `DuplicateUser` → 200, form error shown
- `test_provision_post_email_fails`: POST → `provision_user` succeeds, `send_activation_email` raises `KeycloakConnectionError` → 200, `email_sent=False`, warnings not empty
- `test_provision_post_missing_required`: POST without username → 200, form errors
- `test_provision_post_group_assignment_fails`: POST → `assign_group` raises `KeycloakConnectionError` → 200, warning shown, success still True

---

## Complexity Tracking

No constitution violations.
