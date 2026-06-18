# Tasks: Group-Based Access Control

**Input**: Design documents from `specs/002-group-access-control/`

**References**: [spec.md](spec.md) · [plan.md](plan.md) · [data-model.md](data-model.md) · [research.md](research.md) · [quickstart.md](quickstart.md)

**Tests**: Included — required by project constitution ("every view must have at least one test").

**Organization**: Grouped by user story. Phases 1–2 are foundational and block all user story phases.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story from spec.md (US1–US8)
- Exact file paths in all descriptions

---

## Phase 1: Setup — Keycloak Realm Update

**Purpose**: Extend the identity provider configuration with the 6 new flat groups and update test user assignments. This is the prerequisite for everything — without groups in Keycloak, the JWT carries no group claims.

**⚠️ CRITICAL**: After updating realm-export.json, a full reset is required:
`docker compose down -v && docker compose up --build`

- [X] T001 Add 6 flat groups to `keycloak-django-sso/keycloak/realm-export.json` in the `"groups"` array: `d1:rrhh`, `d1:worker`, `d1:admin`, `d2:viewer`, `d2:editor`, `d2:admin` (each with `"path": "/<name>"` and `"subGroups": []`)
- [X] T002 Update `testadmin` user entry in `keycloak-django-sso/keycloak/realm-export.json`: add `"groups": ["/ops", "/d1:admin", "/d2:admin"]`
- [X] T003 Update `testuser` user entry in `keycloak-django-sso/keycloak/realm-export.json`: add `"groups": ["/team-a", "/d1:worker", "/d2:viewer"]`

**Checkpoint**: `docker compose down -v && docker compose up --build`. Run VS1 + VS2 from quickstart.md to confirm groups exist and test users are assigned.

---

## Phase 2: Foundational — D1 Sync + Decorator + Access Denied

**Purpose**: Backend group sync and decorator for D1. Blocks US1, US2, US3, US7. Can run in parallel with Phase 3.

**⚠️ CRITICAL**: No D1 view can enforce group access until this phase is complete.

- [X] T004 Extend `update_user()` in `keycloak-django-sso/d1/accounts/backends.py`: after existing `UserProfile.objects.filter(...).update(...)`, filter `claims.get('groups', [])` to `d1:*` only, `get_or_create` each as `auth.Group`, then call `user.groups.set(django_groups)` (import `from django.contrib.auth.models import Group`)
- [X] T005 Extend `create_user()` in `keycloak-django-sso/d1/accounts/backends.py`: call `update_user(user, claims)` after `super().create_user(claims)` so first-time login also syncs groups
- [X] T006 Create `keycloak-django-sso/d1/accounts/decorators.py`: implement `require_groups(allowed_groups)` — if not authenticated redirect to `settings.LOGIN_URL + ?next=path`; if authenticated but `user.groups.filter(name__in=allowed_groups).exists()` is False redirect to `/access-denied/?required=<comma-joined>`; otherwise call view function (use `functools.wraps`, log denials)
- [X] T007 Add `GroupAccessDeniedView(TemplateView)` to `keycloak-django-sso/d1/dashboard/views.py`: reads `request.GET.get('required', '')`, splits on comma, passes list to template as `required_groups`
- [X] T008 Add URL pattern `path('access-denied/', GroupAccessDeniedView.as_view(), name='group-access-denied')` to `keycloak-django-sso/d1/dashboard/urls.py`
- [X] T009 Create `keycloak-django-sso/d1/templates/dashboard/access_denied.html`: show "Acceso Denegado" heading, list the `required_groups`, and a back link to `/`

**Checkpoint**: Log in as `testuser` in D1. Run `docker exec d1 python manage.py shell -c "from django.contrib.auth import get_user_model; u = get_user_model().objects.get(username='testuser'); print([g.name for g in u.groups.all()])"`. Expected: `['d1:worker']`. Navigate to `/access-denied/?required=d1:rrhh,d1:admin` — expect the access-denied template.

---

## Phase 3: Foundational — D2 Sync + Decorator + Group-Denied

**Purpose**: Backend group sync and decorator for D2. Blocks US4, US5, US6. **Runs in parallel with Phase 2** (different app, different files).

**⚠️ CRITICAL**: No D2 view can enforce group access until this phase is complete.

- [X] T010 [P] Extend `update_user()` in `keycloak-django-sso/d2/accounts/backends.py`: filter `claims.get('groups', [])` to `d2:*` only, `get_or_create` each as `auth.Group`, call `user.groups.set(django_groups)` (import `from django.contrib.auth.models import Group`)
- [X] T011 [P] Extend `create_user()` in `keycloak-django-sso/d2/accounts/backends.py`: call `update_user(user, claims)` after user creation so first-time login also syncs D2 groups
- [X] T012 [P] Add `require_groups(allowed_groups)` to `keycloak-django-sso/d2/accounts/decorators.py` (same logic as D1 but redirects to `/group-denied/?required=<comma-joined>`; keep existing `require_scope` function unchanged)
- [X] T013 [P] Add `GroupAccessDeniedView(LoginRequiredMixin, TemplateView)` to `keycloak-django-sso/d2/portal/views.py`: reads `request.GET.get('required', '')`, passes split list to template as `required_groups`
- [X] T014 [P] Add URL pattern `path('group-denied/', GroupAccessDeniedView.as_view(), name='group-access-denied')` to `keycloak-django-sso/d2/portal/urls.py`
- [X] T015 [P] Create `keycloak-django-sso/d2/templates/portal/group_access_denied.html`: show "Acceso Denegado" heading, list `required_groups`, distinguish from scope-denied page (`/denied/`)

**Checkpoint**: Log in as `testuser` in D2. Verify `d2/accounts/tests/test_backends.py` shell check shows `['d2:viewer']`. Navigate to `/group-denied/?required=d2:editor,d2:admin` — expect the group-denied template.

---

## Phase 4: US1 — D1 RRHH User Access (Priority: P1) 🎯 MVP

**Goal**: Users in `d1:rrhh` (or `d1:admin`) can access `/rrhh/`; everyone else is redirected to access-denied.

**Independent Test**: Log in as `testuser` (group: `d1:worker`) → `/rrhh/` shows access-denied. Log in as `testadmin` (group: `d1:admin`) → `/rrhh/` shows 200.

- [X] T016 [P] [US1] Add `RRHHView(LoginRequiredMixin, TemplateView)` to `keycloak-django-sso/d1/dashboard/views.py`: apply `@method_decorator(require_groups(['d1:rrhh', 'd1:admin']), name='dispatch')`; `template_name = 'dashboard/rrhh.html'`
- [X] T017 [US1] Add URL pattern `path('rrhh/', RRHHView.as_view(), name='rrhh')` to `keycloak-django-sso/d1/dashboard/urls.py`
- [X] T018 [P] [US1] Create `keycloak-django-sso/d1/templates/dashboard/rrhh.html`: RRHH section page, shows authenticated user's email and groups from `request.user.profile`

**Checkpoint**: VS4 partial from quickstart.md — `testuser` denied at `/rrhh/`, `testadmin` granted.

---

## Phase 5: US2 — D1 Worker User Access (Priority: P1)

**Goal**: Users in `d1:worker` (or `d1:admin`) can access `/worker/`; others get access-denied.

**Independent Test**: `testuser` (group: `d1:worker`) → `/worker/` shows 200. `testadmin` → `/worker/` shows 200. User with only `d1:rrhh` → `/worker/` shows access-denied.

**Can run in parallel with Phase 4** (different view, different template).

- [X] T019 [P] [US2] Add `WorkerView(LoginRequiredMixin, TemplateView)` to `keycloak-django-sso/d1/dashboard/views.py`: apply `@method_decorator(require_groups(['d1:worker', 'd1:admin']), name='dispatch')`; `template_name = 'dashboard/worker.html'`
- [X] T020 [US2] Add URL pattern `path('worker/', WorkerView.as_view(), name='worker')` to `keycloak-django-sso/d1/dashboard/urls.py`
- [X] T021 [P] [US2] Create `keycloak-django-sso/d1/templates/dashboard/worker.html`: Worker section page

**Checkpoint**: VS4 partial — `testuser` granted at `/worker/`, denied at `/rrhh/`.

---

## Phase 6: US3 — D1 Admin Full Access (Priority: P1)

**Goal**: Only users in `d1:admin` can access `/admin/`. They can also access all other D1 pages.

**Independent Test**: `testadmin` → `/admin/` shows 200. `testuser` → `/admin/` shows access-denied.

**Can run in parallel with Phases 4 and 5** (different view, different template).

- [X] T022 [P] [US3] Add `D1AdminView(LoginRequiredMixin, TemplateView)` to `keycloak-django-sso/d1/dashboard/views.py`: apply `@method_decorator(require_groups(['d1:admin']), name='dispatch')`; `template_name = 'dashboard/admin_section.html'`
- [X] T023 [US3] Add URL pattern `path('admin/', D1AdminView.as_view(), name='d1-admin')` to `keycloak-django-sso/d1/dashboard/urls.py`
- [X] T024 [P] [US3] Create `keycloak-django-sso/d1/templates/dashboard/admin_section.html`: D1 Admin section page (not Django admin — just the app-level admin area)

**Checkpoint**: VS5 from quickstart.md — `testadmin` can access all 4 D1 pages.

---

## Phase 7: US7 — D1 Home + No-Group Access Denied (Priority: P3)

**Goal**: A group-gated home page accessible to all D1 groups. Authenticated users without any D1 group see the access-denied page — not the Keycloak login.

**Independent Test**: `testadmin` or `testuser` → `/home/` shows 200. Authenticated user with no `d1:*` groups → `/home/` shows access-denied (not a 302 to Keycloak).

- [X] T025 [P] [US7] Add `D1HomeView(LoginRequiredMixin, TemplateView)` to `keycloak-django-sso/d1/dashboard/views.py`: apply `@method_decorator(require_groups(['d1:rrhh', 'd1:worker', 'd1:admin']), name='dispatch')`; `template_name = 'dashboard/home_groups.html'`; pass user profile and group list to context
- [X] T026 [US7] Add URL pattern `path('home/', D1HomeView.as_view(), name='d1-home')` to `keycloak-django-sso/d1/dashboard/urls.py`
- [X] T027 [P] [US7] Create `keycloak-django-sso/d1/templates/dashboard/home_groups.html`: group-gated home page; shows user's active D1 groups and navigation links to permitted sections

**Checkpoint**: VS4 from quickstart.md — `testuser` at `/home/` shows 200.

---

## Phase 8: US4 — D2 Viewer Sees Reports (Priority: P2)

**Goal**: Add group access control to the existing `/reports/` view. Users need `d2:viewer`, `d2:editor`, or `d2:admin` group (in addition to the existing `read:reports` scope requirement).

**Independent Test**: `testuser` with `d2:viewer` group + `read:reports` scope → `/reports/` shows 200. `testuser` without any `d2:*` groups → `/group-denied/`.

**Can run in parallel with Phase 9 and Phase 10** (overlapping file but only adding decorator line).

- [X] T028 [US4] Add `require_groups` decorator to `ReportsView` in `keycloak-django-sso/d2/portal/views.py`: add `@method_decorator(require_groups(['d2:viewer', 'd2:editor', 'd2:admin']), name='dispatch')` — place it INSIDE the existing `require_scope` decorator so scope is checked first, then group; import `require_groups` from `accounts.decorators`

**Checkpoint**: VS7 from quickstart.md — `testuser` with `d2:viewer` granted at `/reports/`, user without D2 group denied.

---

## Phase 9: US5 — D2 Editor Access (Priority: P2)

**Goal**: New `/editor/` route, accessible to `d2:editor` and `d2:admin` groups.

**Independent Test**: `testadmin` (group: `d2:admin`) → `/editor/` shows 200. `testuser` (group: `d2:viewer`) → `/group-denied/`.

- [X] T029 [P] [US5] Add `EditorView(LoginRequiredMixin, TemplateView)` to `keycloak-django-sso/d2/portal/views.py`: apply `@method_decorator(require_groups(['d2:editor', 'd2:admin']), name='dispatch')`; `template_name = 'portal/editor.html'`
- [X] T030 [US5] Add URL pattern `path('editor/', EditorView.as_view(), name='editor')` to `keycloak-django-sso/d2/portal/urls.py`
- [X] T031 [P] [US5] Create `keycloak-django-sso/d2/templates/portal/editor.html`: editor section page

**Checkpoint**: VS7 partial — `testadmin` granted at `/editor/`, `testuser` denied.

---

## Phase 10: US6 — D2 Admin Full Access (Priority: P2)

**Goal**: New `/admin/` route in D2, accessible only to `d2:admin`.

**Independent Test**: `testadmin` (group: `d2:admin`) → `/admin/` shows 200. `testuser` (group: `d2:viewer`) → `/group-denied/`.

- [X] T032 [P] [US6] Add `D2AdminView(LoginRequiredMixin, TemplateView)` to `keycloak-django-sso/d2/portal/views.py`: apply `@method_decorator(require_groups(['d2:admin']), name='dispatch')`; `template_name = 'portal/admin_section.html'`
- [X] T033 [US6] Add URL pattern `path('admin/', D2AdminView.as_view(), name='d2-admin')` to `keycloak-django-sso/d2/portal/urls.py`
- [X] T034 [P] [US6] Create `keycloak-django-sso/d2/templates/portal/admin_section.html`: D2 admin section page

**Checkpoint**: VS8 from quickstart.md — `testadmin` can access all 3 D2 group-protected pages.

---

## Phase 11: Tests (Constitution-Required)

**Purpose**: Every new and modified view must have at least one test (project constitution rule). Tests verify: authorized user gets 200, unauthorized authenticated user gets redirect to access-denied, unauthenticated user gets redirect to login.

**All test tasks in this phase can run in parallel** — they write to different files.

- [X] T035 [P] Write D1 backend group sync tests in `keycloak-django-sso/d1/accounts/tests/test_backends.py`: (a) `update_user()` with `d1:worker` in claims → `auth.Group('d1:worker')` assigned to user; (b) `update_user()` with empty groups → no D1 groups; (c) `d2:*` groups in claims → NOT assigned in D1
- [X] T036 [P] Create `keycloak-django-sso/d1/accounts/tests/test_decorators.py`: test `require_groups` — authenticated user with matching group → view called; authenticated user without matching group → redirect to `/access-denied/`; unauthenticated → redirect to login
- [X] T037 [P] Extend `keycloak-django-sso/d1/dashboard/tests/test_views.py`: for each new view (RRHHView, WorkerView, D1AdminView, D1HomeView, GroupAccessDeniedView) — test with correct group (200), wrong group (redirect to access-denied), and anonymous (redirect to login)
- [X] T038 [P] Write D2 backend group sync tests in `keycloak-django-sso/d2/accounts/tests/test_backends.py`: same 3 cases as T035 but for `d2:*` prefix
- [X] T039 [P] Extend `keycloak-django-sso/d2/accounts/tests/test_decorators.py`: test `require_groups` in D2 context — correct group → view called; wrong group → redirect to `/group-denied/`; unauthenticated → redirect to login
- [X] T040 [P] Extend `keycloak-django-sso/d2/portal/tests/test_views.py`: for each new/modified view (ReportsView with group, EditorView, D2AdminView, GroupAccessDeniedView) — authorized group (200), unauthorized group (redirect to group-denied), anonymous (redirect to login)

**Checkpoint**: `docker compose exec d1 python manage.py test --verbosity=2` and `docker compose exec d2 python manage.py test --verbosity=2` — all pass.

---

## Phase 12: Polish & Cross-Cutting Concerns

- [X] T041 Run quickstart.md validation scenarios VS1–VS12 in order and confirm all expected outcomes
- [X] T042 Verify cross-app group isolation (VS11 from quickstart.md): D1 `auth_user_groups` contains only `d1:*` names; D2 contains only `d2:*` names
- [ ] T043 Verify US8 (group change takes effect on re-login): assign `d1:rrhh` to `testuser` in Keycloak admin, log out/in, confirm `/rrhh/` grants access, then reverse

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Keycloak) → blocks nothing directly but provides JWT groups
Phase 2 (D1 foundation) → blocks Phases 4, 5, 6, 7
Phase 3 (D2 foundation) → blocks Phases 8, 9, 10
Phases 2 and 3 can run in parallel (different apps)

After Phase 2:
  Phases 4, 5, 6, 7 can run in parallel (different views/files)

After Phase 3:
  Phase 8 (T028 only — modifies existing view)
  Phases 9, 10 can run in parallel with each other (new views/files)

Phase 11 (Tests): After all views are complete (after Phase 10)
Phase 12 (Polish): After all tests pass
```

### User Story Dependencies

| Story | Depends on | Can parallel |
|-------|-----------|--------------|
| US1 (RRHH) | Phase 2 complete | US2, US3, US7 |
| US2 (Worker) | Phase 2 complete | US1, US3, US7 |
| US3 (Admin D1) | Phase 2 complete | US1, US2, US7 |
| US7 (No-group, D1 home) | Phase 2 complete | US1, US2, US3 |
| US4 (D2 Viewer) | Phase 3 complete + Phase 8 | US5, US6 after T028 done |
| US5 (Editor) | Phase 3 complete | US6 |
| US6 (Admin D2) | Phase 3 complete | US5 |
| US8 (Re-login sync) | T004 + T010 | validated in Phase 12 |

### Within Each User Story

- Decorator must exist (Phase 2 or 3) → then views → then templates (can parallel view+template)
- URL pattern added after view exists

---

## Parallel Execution Examples

### Parallel: Phase 2 + Phase 3 (after Phase 1)

```
Agent A → T004, T005, T006, T007, T008, T009  (D1 foundation)
Agent B → T010, T011, T012, T013, T014, T015  (D2 foundation)
```

### Parallel: D1 Views (after Phase 2)

```
Agent A → T016, T017, T018  (RRHH view + URL + template)
Agent B → T019, T020, T021  (Worker view + URL + template)
Agent C → T022, T023, T024  (Admin view + URL + template)
Agent D → T025, T026, T027  (Home view + URL + template)
```

### Parallel: D2 Views (after Phase 3)

```
Agent A → T028                    (add group decorator to ReportsView)
Agent B → T029, T030, T031        (Editor view + URL + template)
Agent C → T032, T033, T034        (D2 Admin view + URL + template)
```

### Parallel: Tests (after all views complete)

```
All of T035–T040 can run simultaneously (different files)
```

---

## Implementation Strategy

### MVP (US1 only — D1 RRHH access)

1. Phase 1: Update realm-export.json (T001–T003) + full reset
2. Phase 2: D1 backend sync + decorator + access-denied (T004–T009)
3. Phase 4: RRHH view (T016–T018)
4. **STOP and VALIDATE**: `testuser` denied at `/rrhh/`, `testadmin` granted
5. Add T035–T036 (tests) for US1 foundation

### Incremental Delivery

1. MVP above → D1 RRHH works
2. Phase 5+6+7 → All D1 group views work
3. Phase 3 → D2 foundation
4. Phase 8+9+10 → All D2 group views work
5. Phase 11 → Full test coverage
6. Phase 12 → Validated against quickstart.md

---

## Notes

- `[P]` = can run in parallel with other `[P]` tasks in same phase
- US8 (group change takes effect on re-login) is covered by T004+T010 — the `user.groups.set()` call handles it; validated manually in T043
- The existing `/admin-panel/` route in D1 is NOT changed — the new `/admin/` is a separate app-level admin section
- The existing `/reports/` scope-gated behavior in D2 is preserved — T028 only ADDS a group check on top
- `d1:admin` and `d2:admin` are app-level admin groups, NOT Keycloak realm admin access
