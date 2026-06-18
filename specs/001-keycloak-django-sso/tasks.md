---
description: "Task list for Keycloak-Django SSO Platform"
---

# Tasks: Keycloak-Django SSO Platform

**Input**: Design documents from `specs/001-keycloak-django-sso/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Included — required by Constitution Principle III (Test-First NON-NEGOTIABLE). Write tests FIRST, verify they FAIL, then implement.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths included in all descriptions

## Path Conventions

Per plan.md structure (multi-service):
- Docker infra: `keycloak-django-sso/` (project root)
- D1 app: `d1/` — `d1/accounts/`, `d1/dashboard/`, `d1/kc_admin/`, `d1/config/settings/`
- D2 app: `d2/` — `d2/accounts/`, `d2/portal/`, `d2/config/settings/`

---

## Phase 1: Setup

**Purpose**: Docker infrastructure and Django project scaffolding. No user story logic yet.

- [x] T001 Create keycloak-django-sso/ project root with d1/, d2/, postgres/, keycloak/ subdirectories
- [x] T002 Create docker-compose.yml: postgres service (healthcheck: pg_isready -U postgres), keycloak service (command: start-dev --import-realm, healthcheck: curl /health/ready, volume: ./keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json, env: KC_DB=postgres KC_DB_URL KC_DB_USERNAME KC_DB_PASSWORD KC_BOOTSTRAP_ADMIN_USERNAME KC_BOOTSTRAP_ADMIN_PASSWORD), d1 service (depends_on: keycloak service_healthy, healthcheck: curl /health/), d2 service (same pattern); keycloak and d1/d2 all depend on postgres with service_healthy condition
- [x] T003 [P] Create postgres/init.sql: CREATE USER keycloak_user/d1_user/d2_user with passwords from env; CREATE DATABASE keycloak_db/d1_db/d2_db owned by respective user; REVOKE ALL ON DATABASE keycloak_db/d1_db/d2_db FROM PUBLIC; GRANT ALL PRIVILEGES ON DATABASE keycloak_db TO keycloak_user (same for d1/d2)
- [x] T004 [P] Create keycloak/realm-export.json: app-realm with d1-client (confidential, Authorization Code, service accounts enabled, redirectUris: http://localhost:8001/oidc/callback/), d2-client (confidential, Authorization Code, redirectUris: http://localhost:8002/oidc/callback/); realm roles: admin, viewer; groups: /team-a, /ops; client scopes: read:reports and write:data (openid-connect, assigned to d2-client); protocol mappers on d1-client: groups mapper (groups claim, full path=false) and realm roles mapper (realm_access.roles); same mappers on d2-client plus scope mapper for read:reports and write:data
- [x] T005 [P] Create .env.example with all required variables: POSTGRES_PASSWORD, POSTGRES_USER=postgres, KEYCLOAK_DB_PASSWORD, D1_DB_PASSWORD, D2_DB_PASSWORD, KC_BOOTSTRAP_ADMIN_PASSWORD, D1_OIDC_CLIENT_SECRET, D2_OIDC_CLIENT_SECRET, D1_SECRET_KEY, D2_SECRET_KEY, KEYCLOAK_SERVER_URL=http://keycloak:8080, D1_DATABASE_URL=postgres://d1_user:password@postgres:5432/d1_db, D2_DATABASE_URL=postgres://d2_user:password@postgres:5432/d2_db, KEYCLOAK_REALM=app-realm, D1_REDIRECT_URI=http://localhost:8001/oidc/callback/, D2_REDIRECT_URI=http://localhost:8002/oidc/callback/, D1_KC_SERVICE_ACCOUNT_CLIENT_ID, D1_KC_SERVICE_ACCOUNT_CLIENT_SECRET
- [x] T006 [P] Create .gitignore: .env, __pycache__/, *.pyc, *.pyo, *.pyd, *.log, db.sqlite3, .DS_Store, .venv/, *.egg-info/, dist/, staticfiles/
- [x] T007 Create d1/ Django project: d1/manage.py (DJANGO_SETTINGS_MODULE=config.settings.development), d1/config/__init__.py, d1/config/wsgi.py, d1/config/settings/__init__.py
- [x] T008 [P] Create d1/Dockerfile (FROM python:3.12-slim, WORKDIR /app, COPY requirements.txt, RUN pip install --no-cache-dir -r requirements.txt, COPY ., CMD gunicorn config.wsgi:application --bind 0.0.0.0:8000) and d1/requirements.txt: Django==5.1.*, mozilla-django-oidc==4.*, python-keycloak==3.*, django-environ==0.11.*, psycopg2-binary==2.*, gunicorn==22.*, PyJWT==2.*, whitenoise==6.*
- [x] T009 Create d1/config/settings/base.py: env() setup with django-environ; SECRET_KEY/DEBUG/ALLOWED_HOSTS from env; INSTALLED_APPS including accounts, dashboard, kc_admin, mozilla_django_oidc, whitenoise.runserver_nostatic; DATABASES from DATABASE_URL env; AUTHENTICATION_BACKENDS = ['accounts.backends.KeycloakOIDCBackend']; OIDC_RP_CLIENT_ID/OIDC_RP_CLIENT_SECRET/OIDC_RP_SIGN_ALGO=RS256 from env; OIDC_OP_AUTHORIZATION_ENDPOINT/OIDC_OP_TOKEN_ENDPOINT/OIDC_OP_USER_ENDPOINT/OIDC_OP_JWKS_ENDPOINT from KEYCLOAK_SERVER_URL+KEYCLOAK_REALM; LOGIN_URL='/oidc/authenticate/'; LOGGING config outputting JSON-style to stdout for auth events; DEFAULT_AUTO_FIELD=BigAutoField
- [x] T010 [P] Create d1/config/settings/development.py (DEBUG=True, ALLOWED_HOSTS=['*'], OIDC_VERIFY_SSL=False) and d1/config/settings/production.py (DEBUG=False, SECURE_SSL_REDIRECT=True, SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
- [x] T011 Create d2/ Django project: d2/manage.py, d2/config/__init__.py, d2/config/wsgi.py, d2/config/settings/__init__.py
- [x] T012 [P] Create d2/Dockerfile and d2/requirements.txt (Django==5.1.*, mozilla-django-oidc==4.*, django-environ==0.11.*, psycopg2-binary==2.*, gunicorn==22.*, PyJWT==2.*, whitenoise==6.*); create d2/config/settings/base.py (INSTALLED_APPS: accounts, portal, mozilla_django_oidc; OIDC_STORE_ACCESS_TOKEN=True; AUTHENTICATION_BACKENDS=['accounts.backends.D2OIDCBackend']; same OIDC_OP_* env pattern as D1 but using D2_OIDC_CLIENT_ID/SECRET; LOGGING config); create d2/config/settings/development.py and d2/config/settings/production.py

**Checkpoint**: Run `docker compose build` — all 4 image builds must succeed without errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core auth infrastructure required by ALL user stories. No story can begin until this phase is complete.

**⚠️ CRITICAL**: No user story implementation until foundation is complete.

- [x] T013 Create d1/accounts/ Django app: d1/accounts/__init__.py, d1/accounts/apps.py (AccountsConfig, name='accounts'), d1/accounts/models.py with UserProfile(user=OneToOneField(AUTH_USER_MODEL, on_delete=CASCADE, related_name='profile'), sub=CharField(max_length=255, unique=True), email=EmailField(blank=True), roles=JSONField(default=list), groups=JSONField(default=list), last_synced_at=DateTimeField(auto_now=True), __str__=lambda self: self.sub)
- [x] T014 [P] Write failing tests for UserProfile model in d1/accounts/tests/__init__.py and d1/accounts/tests/test_models.py: test sub uniqueness constraint raises IntegrityError on duplicate, test roles and groups default to empty list, test cascade delete removes UserProfile when User deleted, test __str__ returns sub value — verify all FAIL before T015
- [x] T015 Generate D1 initial migration: d1/accounts/migrations/__init__.py and d1/accounts/migrations/0001_initial.py for UserProfile (run python manage.py makemigrations accounts from d1/)
- [x] T016 Create d1/accounts/backends.py with KeycloakOIDCBackend(OIDCAuthenticationBackend): create_user(userinfo) creates Django User(username=userinfo['sub'], email=userinfo.get('email','')) then calls user.set_unusable_password() then creates UserProfile(user=user, sub=userinfo['sub'], email=userinfo.get('email',''), roles=[], groups=[]); update_user(user, claims) stub that returns user (full sync implemented in US2 phase); add structured log entry on create_user with action='oidc_user_created', sub=sub
- [x] T017 [P] Write failing tests for KeycloakOIDCBackend in d1/accounts/tests/test_backends.py: test create_user creates Django User with username=sub, test create_user creates UserProfile with correct sub, test set_unusable_password called (user.has_usable_password() is False), test update_user returns user object — verify all FAIL before T016 implementation completes
- [x] T018 Create d1/accounts/urls.py with path('health/', HealthView.as_view(), name='health'); create d1/accounts/views.py with HealthView(View) returning JsonResponse({"status":"ok"}, status=200); update d1/config/urls.py: include('mozilla_django_oidc.urls') at 'oidc/', include('accounts.urls') at ''
- [x] T019 Create d2/accounts/ Django app: d2/accounts/__init__.py, d2/accounts/apps.py (AccountsConfig); create d2/accounts/backends.py with D2OIDCBackend(OIDCAuthenticationBackend): create_user() and update_user() both call self._store_scopes(request, claims) which reads request.session['oidc_access_token'] (set by mozilla-django-oidc OIDC_STORE_ACCESS_TOKEN=True), decodes with PyJWT (no verify, already verified), splits token['scope'] by space, stores list in request.session['oidc_scopes']; log action='oidc_scope_stored', scopes=scopes
- [x] T020 [P] Write failing tests for D2OIDCBackend in d2/accounts/tests/__init__.py and d2/accounts/tests/test_backends.py: test session['oidc_scopes'] set to ['openid','read:reports'] when token scope='openid read:reports', test session['oidc_scopes'] set to [] when token has no scope claim, test scopes overwritten (not appended) on re-login — verify all FAIL before T019 implementation
- [x] T021 Create d2/accounts/decorators.py with require_scope(scope_name) decorator: if not request.user.is_authenticated → redirect(settings.LOGIN_URL + '?next=' + request.path); if scope_name not in request.session.get('oidc_scopes',[]) → redirect(f'/denied/?required={scope_name}'); else call view_func; create d2/accounts/mixins.py with ScopeRequiredMixin(LoginRequiredMixin): required_scope = None; dispatch() checks session scopes and redirects to denied if absent
- [x] T022 [P] Write failing tests for @require_scope in d2/accounts/tests/test_decorators.py: test authenticated user with scope gets 200, test authenticated user without scope gets 302 to /denied/?required=read:reports, test unauthenticated user gets 302 to LOGIN_URL — verify all FAIL before T021 implementation
- [x] T023 Create d2/accounts/views.py: LogoutView(OIDCLogoutView or View calling logout+redirect), DeniedView(LoginRequiredMixin, TemplateView, template_name='accounts/denied.html', get_context_data adds required_scope=request.GET.get('required','')), HealthView(View returning JsonResponse({"status":"ok"})); create d2/accounts/urls.py with health/, denied/, logout/ paths; update d2/config/urls.py: include oidc/, include accounts.urls at ''
- [x] T024 Create d2/accounts/migrations/ (__init__.py only — D2 has no custom models); run python manage.py migrate for both d1 and d2 inside Docker; run python manage.py check for both — confirm zero errors

**Checkpoint**: Foundation ready. `docker compose up` should start all services healthy. D1 /health/ returns 200. D2 /health/ returns 200. OIDC redirect to Keycloak works from both apps (even if callback fails without real client secrets configured).

---

## Phase 3: User Story 1 — Admin Manages Keycloak Users (Priority: P1) 🎯 MVP

**Goal**: Five D1 JSON endpoints (list, create, assign role, assign group, deactivate) call Keycloak Admin REST API and return correct responses.

**Independent Test**: Quickstart VS4–VS7 — login to D1, use session cookie to call each /api/users/ endpoint, verify Keycloak reflects changes.

### Tests for User Story 1 ⚠️ WRITE FIRST — VERIFY FAIL BEFORE IMPLEMENTING T031+

- [x] T025 [P] [US1] Write failing tests for GET /api/users/ in d1/kc_admin/tests/__init__.py and d1/kc_admin/tests/test_views.py: mock KeycloakAdminClient.list_users to return [{id,username,email,enabled,roles,groups}]; test authenticated GET returns 200 JSON with {"users":[...]}, test unauthenticated GET returns 401 JSON {"error":"Authentication required"}, test GET returns 502 when list_users raises KeycloakConnectionError
- [x] T026 [P] [US1] Write failing tests for POST /api/users/create/ in d1/kc_admin/tests/test_views.py: test 201 {"id":..,"email":..,"username":..} on valid body, test 400 {"error":"Fields required: email, username"} when email missing, test 409 {"error":"User with this username or email already exists"} when DuplicateUser raised, test 401 when unauthenticated
- [x] T027 [P] [US1] Write failing tests for POST /api/users/<sub>/roles/assign/ in d1/kc_admin/tests/test_views.py: test 200 {"success":true,"user_id":sub,"role":"admin"} on success, test 400 when role_name missing from body, test 404 {"error":"User or role not found"} when UserNotFound or RoleNotFound raised, test 401 when unauthenticated
- [x] T028 [P] [US1] Write failing tests for POST /api/users/<sub>/groups/assign/ in d1/kc_admin/tests/test_views.py: test 200 {"success":true,"user_id":sub,"group":"team-a"} on success, test 404 when GroupNotFound raised, test 401 when unauthenticated
- [x] T029 [P] [US1] Write failing tests for POST /api/users/<sub>/deactivate/ in d1/kc_admin/tests/test_views.py: test 200 {"success":true,"user_id":sub,"enabled":false}, test 404 when UserNotFound, test 409 {"error":"Cannot deactivate your own account"} when sub matches request.user.username, test 401 when unauthenticated
- [x] T030 [P] [US1] Write failing unit tests for KeycloakAdminClient in d1/kc_admin/tests/test_client.py: mock KeycloakAdmin constructor from env vars; test list_users() returns Python list from keycloak_admin.get_users(); test create_user() calls keycloak_admin.create_user() and returns new user id; test assign_realm_role() calls get_realm_role() then assign_realm_roles(); test assign_group() calls get_groups() to find group id then group_user_add(); test deactivate_user() calls update_user(user_id, {"enabled":False}); test KeycloakError in list_users raises KeycloakConnectionError

### Implementation for User Story 1

- [x] T031 [US1] Create d1/kc_admin/ app: d1/kc_admin/__init__.py, d1/kc_admin/apps.py (KcAdminConfig, name='kc_admin')
- [x] T032 [US1] Implement d1/kc_admin/client.py: define typed exceptions UserNotFound/RoleNotFound/GroupNotFound/DuplicateUser/KeycloakConnectionError; define KeycloakAdminClient class that initializes KeycloakAdmin(server_url=env('KEYCLOAK_SERVER_URL'), realm_name=env('KEYCLOAK_REALM'), client_id=env('D1_KC_SERVICE_ACCOUNT_CLIENT_ID'), client_secret_key=env('D1_KC_SERVICE_ACCOUNT_CLIENT_SECRET'), grant_type='client_credentials'); implement list_users() calling get_users() with brief=False; implement create_user(email,username,first_name,last_name) calling create_user(payload,exist_ok=False), map 409 KeycloakError to DuplicateUser; implement assign_realm_role(user_id,role_name) calling get_realm_role(role_name) then assign_realm_roles(); implement assign_group(user_id,group_name) calling get_groups(query={'search':group_name}) then group_user_add(); implement deactivate_user(user_id) calling update_user(user_id,{'enabled':False}); wrap all KeycloakError in typed exceptions; log every call with structured logger (action, target, result, duration_ms)
- [x] T033 [US1] Implement d1/kc_admin/views.py: import get_object_or_404, JsonResponse, login_required, require_http_methods; define kc_client = KeycloakAdminClient() module-level singleton; UsersListView: @login_required GET, returns JsonResponse({"users": kc_client.list_users()}); CreateUserView: @login_required POST, parse JSON body, validate email+username, call kc_client.create_user(), return 201; AssignRoleView: @login_required POST, call kc_client.assign_realm_role(), return 200; AssignGroupView: @login_required POST, call kc_client.assign_group(), return 200; DeactivateUserView: @login_required POST, check request.user.username != sub (409 if same), call kc_client.deactivate_user(), return 200; catch typed exceptions and return correct HTTP status per d1-admin-api.md contract
- [x] T034 [US1] Create d1/kc_admin/urls.py: path('users/', UsersListView, name='users-list'), path('users/create/', CreateUserView, name='users-create'), path('users/<str:sub>/roles/assign/', AssignRoleView, name='users-assign-role'), path('users/<str:sub>/groups/assign/', AssignGroupView, name='users-assign-group'), path('users/<str:sub>/deactivate/', DeactivateUserView, name='users-deactivate'); add path('api/', include('kc_admin.urls')) to d1/config/urls.py
- [x] T035 [US1] Create d1/dashboard/ app: d1/dashboard/__init__.py, d1/dashboard/apps.py (DashboardConfig); add dashboard to INSTALLED_APPS in d1/config/settings/base.py
- [x] T036 [US1] Create d1/dashboard/views.py AdminPanelView(@login_required TemplateView, template_name='dashboard/admin_panel.html'); create d1/dashboard/urls.py with path('admin-panel/', AdminPanelView, name='admin-panel'); add include('dashboard.urls') to d1/config/urls.py; create d1/dashboard/templates/dashboard/admin_panel.html with HTML sections for each operation (list users table, create user form, assign role form, assign group form, deactivate button) using vanilla JavaScript fetch() calls to /api/users/ endpoints (no JS framework — plain fetch with JSON)

**Checkpoint**: Quickstart VS4–VS7 pass. All 5 kc_admin endpoints return correct status codes and response bodies. Admin panel page accessible at /admin-panel/.

---

## Phase 4: User Story 2 — Regular User Auth + Protected D1 Pages (Priority: P2)

**Goal**: Full D1 OIDC login → UserProfile sync (sub, email, roles, groups) → dashboard/profile pages → logout.

**Independent Test**: Quickstart VS2–VS3 — login with browser, verify redirect flow works, UserProfile populated with correct Keycloak data.

### Tests for User Story 2 ⚠️ WRITE FIRST — VERIFY FAIL BEFORE IMPLEMENTING T040+

- [x] T037 [P] [US2] Write failing tests for D1 DashboardView in d1/dashboard/tests/__init__.py and d1/dashboard/tests/test_views.py: test GET /dashboard/ returns 302 to OIDC login when unauthenticated, test GET /dashboard/ returns 200 when authenticated (use force_login), test response context contains 'profile' with roles and groups attributes
- [x] T038 [P] [US2] Write failing tests for D1 profile view in d1/accounts/tests/test_views.py: test GET /profile/ returns 302 when unauthenticated, test GET /profile/ returns 200 with profile.sub, profile.email, profile.roles, profile.groups in context
- [x] T039 [P] [US2] Write failing tests for UserProfile sync in d1/accounts/tests/test_backends.py: test update_user() extracts roles from claims['realm_access']['roles'] and saves to UserProfile.roles, test update_user() extracts groups from claims.get('groups',[]) and saves to UserProfile.groups, test update_user() overwrites roles/groups (does not append), test update_user() updates email from claims, test system roles (uma_authorization, default-roles-*) excluded from roles list

### Implementation for User Story 2

- [x] T040 [US2] Implement full UserProfile sync in d1/accounts/backends.py KeycloakOIDCBackend.update_user(user, claims): extract roles = [r for r in claims.get('realm_access',{}).get('roles',[]) if not r.startswith('default-roles') and r not in ('uma_authorization','offline_access')]; extract groups = claims.get('groups',[]); update UserProfile via UserProfile.objects.filter(user=user).update(email=claims.get('email',''), roles=roles, groups=groups); log action='oidc_profile_synced', sub=user.username, roles_count=len(roles), groups_count=len(groups); return user
- [x] T041 [US2] Implement d1/dashboard/views.py: HomeView(TemplateView, template_name='dashboard/home.html') with no auth required; DashboardView(LoginRequiredMixin, TemplateView, template_name='dashboard/dashboard.html') with get_context_data adding profile=request.user.profile; register in d1/dashboard/urls.py as path('', HomeView, name='home'), path('dashboard/', DashboardView, name='dashboard'); add include('dashboard.urls') to d1/config/urls.py
- [x] T042 [US2] Create D1 templates directory d1/dashboard/templates/dashboard/: base.html (HTML5 base with nav links: Dashboard / Profile / Admin Panel / Logout), home.html (welcome page with login button linking to /oidc/authenticate/), dashboard.html (shows user.email, profile.roles as list, profile.groups as list, profile.last_synced_at)
- [x] T043 [US2] Implement d1/accounts/views.py ProfileView(LoginRequiredMixin, TemplateView, template_name='accounts/profile.html') with get_context_data adding profile=request.user.profile; implement LogoutView(View) that calls django.contrib.auth.logout(request) and redirects to Keycloak end_session_endpoint URL (OIDC_OP_LOGOUT_ENDPOINT from settings) with id_token_hint and post_logout_redirect_uri params; add logout/ and profile/ paths to d1/accounts/urls.py
- [x] T044 [US2] Create d1/accounts/templates/accounts/: profile.html showing sub, email, roles list, groups list, last_synced_at timestamp
- [x] T045 [US2] Update d1/config/urls.py to include all app URLs (oidc/, accounts/, dashboard/, api/); verify LOGIN_URL and LOGIN_REDIRECT_URL in settings point to correct paths; confirm middleware includes mozilla_django_oidc.middleware.SessionRefresh (optional: add for session freshness)

**Checkpoint**: Quickstart VS2–VS3 pass. Browser login → Keycloak → D1 redirect → dashboard shows email/roles/groups. Profile page shows sub. Logout clears session.

---

## Phase 5: User Story 3 + 4 — D2 Scope Enforcement (Priority: P3 + P4)

**Goal**: D2 pages enforce OAuth2 scope requirements. Users with scope see content; users without scope see Access Denied.

**Independent Test**: Quickstart VS8–VS9 — login with user that has/lacks read:reports scope; verify correct page served.

### Tests for User Stories 3+4 ⚠️ WRITE FIRST — VERIFY FAIL BEFORE IMPLEMENTING T051+

- [x] T046 [P] [US3] Write failing tests for D2 HomeView in d2/portal/tests/__init__.py and d2/portal/tests/test_views.py: test GET / returns 302 to OIDC login when unauthenticated, test GET / returns 200 when authenticated, test response context includes user_scopes matching session['oidc_scopes']
- [x] T047 [P] [US3] Write failing test for D2 ReportsView (scope granted) in d2/portal/tests/test_views.py: set request.session['oidc_scopes']=['openid','read:reports'], test GET /reports/ returns 200
- [x] T048 [P] [US4] Write failing test for D2 ReportsView (scope denied) in d2/portal/tests/test_views.py: set request.session['oidc_scopes']=['openid'], test GET /reports/ returns 302 to /denied/?required=read:reports
- [x] T049 [P] [US3] Write failing tests for D2 DataView in d2/portal/tests/test_views.py: test 200 when session has 'write:data', test 302 to /denied/?required=write:data when 'write:data' absent
- [x] T050 [P] [US4] Write failing tests for D2 DeniedView in d2/accounts/tests/test_views.py: test GET /denied/?required=read:reports returns 200 with required_scope='read:reports' in context, test GET /denied/ (no query param) returns 200 with required_scope='' in context, test GET /denied/ when unauthenticated returns 302 to OIDC login

### Implementation for User Stories 3+4

- [x] T051 [P] [US3] Create d2/portal/ app: d2/portal/__init__.py, d2/portal/apps.py (PortalConfig, name='portal'); add portal to INSTALLED_APPS in d2/config/settings/base.py
- [x] T052 [US3] Implement d2/portal/views.py: HomeView(LoginRequiredMixin, TemplateView, template_name='portal/home.html') with get_context_data adding user_scopes=request.session.get('oidc_scopes',[]); ReportsView(@require_scope('read:reports'), LoginRequiredMixin, TemplateView, template_name='portal/reports.html'); DataView(@require_scope('write:data'), LoginRequiredMixin, TemplateView, template_name='portal/data.html'); create d2/portal/urls.py with path('',HomeView,'home'), path('reports/',ReportsView,'reports'), path('data/',DataView,'data'); add include('portal.urls') to d2/config/urls.py
- [x] T053 [US4] Ensure d2/accounts/views.py DeniedView passes required_scope=request.GET.get('required','') and user_scopes=request.session.get('oidc_scopes',[]) to template context; add path('denied/', DeniedView, name='denied') to d2/accounts/urls.py if not already present
- [x] T054 [US3] Create D2 templates at d2/portal/templates/portal/: base.html (nav: Home / Reports / Data / Logout, shows current user email), home.html (shows user_scopes list as badges, links to /reports/ and /data/ with scope labels), reports.html (reports content placeholder), data.html (data-write content placeholder)
- [x] T055 [US4] Create d2/accounts/templates/accounts/: denied.html (bold 'Access Denied' heading, 'You need the {{ required_scope }} scope to view this page' text, 'Your current scopes: {{ user_scopes|join:", " }}', link back to /)

**Checkpoint**: Quickstart VS8–VS9 pass. D2 scope grant and denial both work correctly. /denied/ page shows the required scope name.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Observability verification, secret hygiene validation, end-to-end stack validation.

- [x] T056 [P] Verify D1 structured logging: trigger create_user (log auth event), update_user sync, each kc_admin operation, and a kc_admin connection error; confirm each produces a log entry with fields: action, sub/user_id, result, timestamp; confirm no token values or client_secret appear in any log line (Principle V)
- [x] T057 [P] Verify D2 structured logging: trigger login (scope stored event), successful scope check, failed scope check; confirm each produces a structured log entry; confirm no access_token value appears in log output (Principle V)
- [x] T058 [P] Run quickstart.md VS1: execute docker compose up --build from clean state; confirm all 4 services reach healthy within 90s; run docker compose exec postgres psql -U postgres -c "\l" and confirm keycloak_db/d1_db/d2_db present; confirm app-realm available at http://localhost:8080/realms/app-realm/.well-known/openid-configuration
- [x] T059 [P] Run quickstart.md VS10 secret hygiene check: grep -rn 'password\|secret\|client_secret' d1/ d2/ keycloak/ postgres/ --include='*.py' --include='*.json' --include='*.yml' excluding .env and tests; confirm .env appears in .gitignore; confirm no credential values exist in source files
- [x] T060 Run python manage.py check --deploy for d1 (using production settings via DJANGO_SETTINGS_MODULE=config.settings.production) and d2; fix any critical warnings; confirm zero errors
- [x] T061 Run full end-to-end validation: execute quickstart.md VS2–VS9 scenarios against live docker compose stack; confirm each scenario produces expected HTTP responses and side effects in Keycloak

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; T003/T004/T005/T006/T008/T010/T012 can all run in parallel after T001/T007/T011
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 completion — T025–T030 (tests) and T031–T036 (impl) sequence within
- **US2 (Phase 4)**: Depends on Phase 2 completion — can run in parallel with Phase 3 (different files)
- **US3+US4 (Phase 5)**: Depends on Phase 2 completion — can run in parallel with Phases 3 and 4 (D2 is fully independent of D1)
- **Polish (Phase 6)**: Depends on Phases 3, 4, 5 completion

### Within Each User Story

1. Write test tasks (T0xx [P] marked) — all can run in parallel with each other
2. **Verify ALL tests FAIL** before writing any implementation
3. Create app scaffolding (T031 pattern) before implementing
4. Implement integration module / client (T032 pattern) before views
5. Implement views (T033 pattern) before URLs
6. Register URLs (T034 pattern) before templates
7. Create templates last

### Parallel Opportunities

- Phase 1: T003, T004, T005, T006, T008, T010, T012 all parallel
- Phase 2: T014, T017, T020, T022 (test tasks) parallel; T013→T015→T016, T019→T021→T023 sequential within D1 and D2 chains
- Phase 3 tests: T025, T026, T027, T028, T029, T030 all parallel
- Phase 4 tests: T037, T038, T039 all parallel
- Phase 5 tests: T046, T047, T048, T049, T050 all parallel
- D1 work (Phases 3+4) and D2 work (Phase 5) can run in parallel after Phase 2

---

## Parallel Example: User Story 1 Tests

```bash
# All test writing tasks for US1 run in parallel:
Task: "Write failing tests for GET /api/users/ in d1/kc_admin/tests/test_views.py"     # T025
Task: "Write failing tests for POST /api/users/create/ in d1/kc_admin/tests/test_views.py"  # T026
Task: "Write failing tests for roles/assign in d1/kc_admin/tests/test_views.py"        # T027
Task: "Write failing tests for groups/assign in d1/kc_admin/tests/test_views.py"       # T028
Task: "Write failing tests for deactivate in d1/kc_admin/tests/test_views.py"          # T029
Task: "Write failing unit tests for KeycloakAdminClient in d1/kc_admin/tests/test_client.py"  # T030
```

---

## Implementation Strategy

### MVP First (User Story 1 Only — D1 Admin API)

1. Complete Phase 1: Setup (docker infra + project scaffold)
2. Complete Phase 2: Foundational (OIDC backends + UserProfile model)
3. Complete Phase 3: US1 kc_admin endpoints
4. **STOP and VALIDATE**: Test all 5 admin API endpoints with session cookie (quickstart VS4–VS7)
5. Demo: admin can create/assign/list/deactivate users in Keycloak from D1

### Incremental Delivery

1. Phase 1 + Phase 2 → Foundation ready; health checks pass; OIDC redirect works
2. Phase 3 → Admin API ready (MVP: D1 user management functional)
3. Phase 4 → Full D1 UX: login → UserProfile sync → dashboard → profile → logout
4. Phase 5 → D2: scope enforcement demo complete
5. Phase 6 → Polish: logging verified, secrets clean, full stack validated

### Parallel Team Strategy

With two developers:
- Dev A: Phase 3 (US1 — D1 kc_admin) after Phase 2 complete
- Dev B: Phase 5 (US3+US4 — D2 scope enforcement) after Phase 2 complete
- Phase 4 (US2 — D1 pages) follows Phase 3 or runs alongside if a third dev is available

---

## Notes

- `[P]` tasks write to different files — verify no file conflicts before parallelizing
- `[US*]` label maps task to user story for traceability and independent testing
- Constitution Principle III is NON-NEGOTIABLE: tests MUST be written and confirmed failing before any implementation starts in each phase
- D1 and D2 are fully independent Django projects — no shared code or imports between them
- All Keycloak Admin API calls go through `d1/kc_admin/client.py` ONLY — no direct KeycloakAdmin calls in views
- Commit after each checkpoint, not after each individual task
