# Tasks: D3 Django Service

**Input**: Design documents from `specs/005-d3-django-service/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: Incluidos — cada vista tiene al menos un test (constitución).

**Organization**: Tasks agrupados por user story para permitir implementación y validación independiente de cada historia.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede correr en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2, US3)
- Rutas relativas desde `keycloak-django-sso/`

---

## Phase 1: Setup (Estructura del Proyecto)

**Purpose**: Crear la estructura de directorios y archivos base de D3 antes de cualquier lógica.

- [x] T001 Crear estructura de directorios `d3/` según plan.md: `config/settings/`, `accounts/migrations/`, `accounts/tests/`, `portal/tests/`, `portal/templates/portal/`
- [x] T002 [P] Crear `d3/requirements.txt` con Django 5.1.*, mozilla-django-oidc 4.*, django-environ 0.11.*, psycopg2-binary 2.*, gunicorn 22.*, PyJWT 2.*, whitenoise 6.*, pytest 8.3.*, pytest-django 4.9.*
- [x] T003 [P] Crear `d3/Dockerfile` copiando `d1/Dockerfile` literalmente (python:3.12-slim, gunicorn CMD con migrate)
- [x] T004 [P] Crear `d3/manage.py` copiando `d1/manage.py` y cambiando DJANGO_SETTINGS_MODULE a `config.settings.development`
- [x] T005 [P] Crear `d3/pytest.ini` y `d3/conftest.py` copiando de `d1/` y ajustando DJANGO_SETTINGS_MODULE

---

## Phase 2: Foundational (Prerequisitos Bloqueantes)

**Purpose**: Infraestructura compartida que DEBE estar completa antes de implementar cualquier user story.

**⚠️ CRÍTICO**: Ninguna user story puede comenzar hasta que esta fase esté completa.

- [x] T006 Añadir `d3_user` y `d3_db` al final de `postgres/init.sql` siguiendo el patrón de D1/D2 (CREATE USER, CREATE DATABASE, REVOKE, GRANT)
- [x] T007 Añadir servicio `d3` a `keycloak-django-sso/docker-compose.yml` con port 8003:8000, variables D3_*, depends_on keycloak+postgres con healthcheck, healthcheck en `/health/`
- [x] T008 [P] Añadir variables `D3_SECRET_KEY`, `D3_DB_PASSWORD`, `D3_OIDC_CLIENT_SECRET`, `D3_OIDC_CLIENT_ID` a `keycloak-django-sso/.env.example`
- [x] T009 [P] Crear `d3/config/__init__.py` (vacío) y `d3/config/wsgi.py` copiando de `d1/config/wsgi.py`
- [x] T010 Crear `d3/config/settings/base.py` con INSTALLED_APPS, MIDDLEWARE (con SessionRefresh), DATABASES via D3_DATABASE_URL, OIDC settings apuntando a d3-client (endpoints KC internos via KEYCLOAK_SERVER_URL), LOGIN_URL='/oidc/authenticate/', SESSION_ENGINE db, STATICFILES whitenoise
- [x] T011 [P] Crear `d3/config/settings/development.py` con DEBUG=True, EMAIL_BACKEND consola
- [x] T012 [P] Crear `d3/config/settings/production.py` con DEBUG=False, SECURE_* headers
- [x] T013 Añadir entidades D3 a `keycloak/realm-export.json`: (a) 3 grupos d3:normas/d3:documentos/d3:leyes al array `groups`; (b) cliente `d3-client` al array `clients`; (c) roles `d3-client: [can-login]` en `roles.client`; (d) authenticatorConfig `d3-client-role-cfg` (condUserRole: d3-client.can-login, negate: true); (e) 5 flujos de autenticación: D3 Browser Flow, d3-client-auth-methods, d3-client-forms, d3-client-otp, d3-client-role-check — usando los UUIDs de `data-model.md`
- [x] T014 Crear `d3/accounts/models.py` con `UserProfile` (OneToOne auth.User, sub CharField, email EmailField, roles JSONField, groups JSONField, last_synced_at DateTimeField) y `d3/accounts/migrations/0001_initial.py`
- [x] T015 Crear `d3/accounts/backends.py` con `D3KeycloakOIDCBackend(OIDCAuthenticationBackend)`: `create_user()` establece `set_unusable_password()`, `update_user()` sincroniza grupos con prefijo `d3:` desde claims, actualiza `UserProfile`
- [x] T016 [P] Crear `d3/accounts/decorators.py` con `require_groups(allowed_groups)` — idéntico a `d1/accounts/decorators.py`: comprueba `request.user.groups.filter(name__in=allowed_groups)`, redirige a `/access-denied/?required=<group>` si falla
- [x] T017 Crear `d3/config/urls.py` con `path('oidc/', include('mozilla_django_oidc.urls'))`, `path('', include('accounts.urls'))`, `path('', include('portal.urls'))`
- [x] T018 [P] Crear `d3/accounts/__init__.py`, `d3/accounts/apps.py`, `d3/portal/__init__.py`, `d3/portal/apps.py`

**Checkpoint**: Estructura completa, BD y Keycloak configurados. Las user stories pueden comenzar.

---

## Phase 3: User Story 1 — Autenticación y can-login (Priority: P1) 🎯 MVP

**Goal**: Un usuario con `can-login` en `d3-client` puede autenticarse en D3. Un usuario sin ese rol es rechazado en Keycloak. D3 muestra la página de inicio al usuario autenticado.

**Independent Test**: Navegar a `http://localhost:8003/` sin sesión → redirige a Keycloak → login con `d3_all_user` → sesión activa en D3. Login con `d3_no_access_user` → Keycloak deniega (quickstart Scenario 1 + 2).

### Implementation for User Story 1

- [x] T019 [US1] Crear `d3/accounts/views.py` con `HealthView` (retorna `{"status": "ok"}`, no requiere login) y `ProfileView` (LoginRequiredMixin, muestra sub + email + groups del UserProfile)
- [x] T020 [P] [US1] Crear `d3/accounts/urls.py` con `path('health/', HealthView.as_view(), name='health')` y `path('profile/', ProfileView.as_view(), name='profile')`
- [x] T021 [US1] Crear `d3/portal/views.py` con `HomeView(LoginRequiredMixin, TemplateView)` template `portal/home.html` — muestra lista de secciones disponibles según grupos del usuario
- [x] T022 [P] [US1] Crear `d3/portal/urls.py` con `path('', HomeView.as_view(), name='home')` y `path('access-denied/', AccessDeniedView.as_view(), name='access-denied')` (AccessDeniedView también en portal/views.py, sin login requerido)
- [x] T023 [P] [US1] Crear `d3/portal/templates/portal/home.html` — base template + lista de secciones disponibles (normas/documentos/leyes) con link condicional según grupos del contexto
- [x] T024 [P] [US1] Crear `d3/portal/templates/portal/access_denied.html` — mensaje de acceso denegado mostrando `?required=` del query string
- [x] T025 [US1] Crear `d3/accounts/tests/__init__.py` y `d3/accounts/tests/test_views.py` — tests: `GET /health/` retorna 200 (sin auth); `GET /profile/` sin sesión retorna redirect 302 a `/oidc/authenticate/`
- [x] T026 [P] [US1] Crear `d3/accounts/tests/test_models.py` — test: crear UserProfile, verificar str, verificar campos JSONField por defecto
- [x] T027 [P] [US1] Crear `d3/accounts/tests/test_backends.py` — test: `update_user()` con claims que incluyen grupos `['d3:normas', 'other:group', 'd1:admin']` — solo `d3:normas` se sincroniza a Django groups

**Checkpoint**: `docker compose up -d` → `http://localhost:8003/` → redirige a Keycloak → login funciona. Usuario sin `can-login` es rechazado. Quickstart Scenarios 1 y 2 pasan.

---

## Phase 4: User Story 2 — Rutas Protegidas por Grupo (Priority: P2)

**Goal**: Las rutas `/normas/`, `/documentos/` y `/leyes/` son accesibles únicamente a usuarios con el grupo correspondiente. Usuarios sin el grupo ven la página de acceso denegado.

**Independent Test**: Login con `d3_normas_user` (solo `d3:normas`) → `/normas/` OK, `/documentos/` → access-denied, `/leyes/` → access-denied (quickstart Scenarios 3 + 4).

### Implementation for User Story 2

- [x] T028 [US2] Añadir `NormasView`, `DocumentosView`, `LeyesView` a `d3/portal/views.py` — cada una usa `LoginRequiredMixin` y `@method_decorator(require_groups(['d3:normas']))` (etc.) en `dispatch()`, con su template correspondiente
- [x] T029 [P] [US2] Actualizar `d3/portal/urls.py` añadiendo `path('normas/', NormasView.as_view(), name='normas')`, `path('documentos/', DocumentosView.as_view(), name='documentos')`, `path('leyes/', LeyesView.as_view(), name='leyes')`
- [x] T030 [P] [US2] Crear `d3/portal/templates/portal/normas.html` — muestra título "Normas" y contenido informativo estático
- [x] T031 [P] [US2] Crear `d3/portal/templates/portal/documentos.html` — muestra título "Documentos" y contenido informativo estático
- [x] T032 [P] [US2] Crear `d3/portal/templates/portal/leyes.html` — muestra título "Leyes" y contenido informativo estático
- [x] T033 [US2] Crear `d3/portal/tests/__init__.py` y `d3/portal/tests/test_views.py` — tests: `GET /normas/` sin sesión → 302; con sesión y grupo `d3:normas` → 200; con sesión sin grupo → redirect a `/access-denied/`; mismos casos para `/documentos/` y `/leyes/`
- [x] T034 [P] [US2] Crear `d3/accounts/tests/test_decorators.py` — test: `require_groups` con usuario con grupo correcto → 200; con usuario sin grupo → redirect a `/access-denied/?required=d3:normas`

**Checkpoint**: Las tres rutas funcionan con control de grupo. Quickstart Scenarios 3 y 4 pasan.

---

## Phase 5: User Story 3 — Logout Explícito (Priority: P3)

**Goal**: El usuario puede cerrar sesión explícitamente. La sesión Django termina y Keycloak es notificado via redirect logout con `id_token_hint`.

**Independent Test**: Login con `d3_all_user` → logout → navegar a `/` → redirige a Keycloak (sin sesión previa reutilizada). Quickstart Scenario 5.

### Implementation for User Story 3

- [x] T035 [US3] Añadir `LogoutView` a `d3/accounts/views.py`: borra la sesión Django, redirige al endpoint de logout de Keycloak con `id_token_hint` y `post_logout_redirect_uri=http://localhost:8003/` (mismo patrón que `d1/accounts/views.py`)
- [x] T036 [P] [US3] Actualizar `d3/accounts/urls.py` añadiendo `path('logout/', LogoutView.as_view(), name='logout')`
- [x] T037 [P] [US3] Añadir enlace "Cerrar sesión" al template base o a `d3/portal/templates/portal/home.html`

**Checkpoint**: Logout funciona. Quickstart Scenario 5 pasa.

---

## Phase 6: Polish & Validación Final

**Purpose**: Verificación end-to-end contra quickstart.md y confirmación de no-regresión en D1/D2.

- [ ] T038 Ejecutar `docker compose down --volumes && docker compose up -d` para verificar arranque limpio con reimportación de realm (requiere acción manual del usuario)
- [ ] T039 [P] Validar Quickstart Scenario 1: login con `d3_all_user` → sesión activa en D3 (requiere T038)
- [ ] T040 [P] Validar Quickstart Scenario 2: login con `d3_no_access_user` → Keycloak deniega (requiere T038)
- [ ] T041 [P] Validar Quickstart Scenario 3: acceso a `/normas/`, `/documentos/`, `/leyes/` con usuario con los 3 grupos (requiere T038)
- [ ] T042 [P] Validar Quickstart Scenario 4: acceso denegado con `d3_normas_user` en `/documentos/` y `/leyes/` (requiere T038)
- [ ] T043 [P] Validar Quickstart Scenario 5: logout limpio (requiere T038)
- [ ] T044 [P] Validar Quickstart Scenario 6: D1 en `http://localhost:8001/` funciona igual, D2 en `http://localhost:8002/` funciona igual (requiere T038)
- [x] T045 [P] Ejecutar tests de D3: `docker compose exec d3 pytest` — todos deben pasar (31/31 ✓)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias — puede comenzar inmediatamente
- **Foundational (Phase 2)**: Depende de Phase 1 — BLOQUEA todas las user stories
- **US1 (Phase 3)**: Depende de Phase 2. Puede comenzar en paralelo con US2/US3 una vez Phase 2 completa
- **US2 (Phase 4)**: Depende de Phase 2. Puede comenzar en paralelo con US1/US3 (pero en la práctica US2 añade vistas a archivos creados en US1 — hacerlos secuencialmente es más simple)
- **US3 (Phase 5)**: Depende de Phase 2. Puede hacerse en paralelo con US1/US2 (añade LogoutView a accounts/views.py — necesita que US1 lo haya creado primero)
- **Polish (Phase 6)**: Depende de US1 + US2 + US3 completas

### User Story Dependencies

- **US1 (P1)**: Independiente tras Phase 2. Es el MVP mínimo — sin US1, nada más funciona.
- **US2 (P2)**: Independiente tras Phase 2. Reutiliza `require_groups` (T016) y `portal/views.py` (T021) de US1 — hacerlo después de US1 es natural.
- **US3 (P3)**: Independiente tras Phase 2. Añade `LogoutView` al `accounts/views.py` creado en US1 (T019) — hacerlo después de US1 es natural.

### Within Each User Story

- Template antes del view que lo usa
- View antes de la URL que lo registra
- URLs antes de los tests que las usan

### Parallel Opportunities

- T002, T003, T004, T005 (Phase 1) — todos en paralelo
- T008, T009, T011, T012, T016, T018 (Phase 2) — en paralelo entre sí (archivos distintos)
- T006, T007, T013, T014, T015 (Phase 2) — secuenciales entre sí por compartir archivos compartidos
- T020, T023, T024 (Phase 3) — en paralelo con T019
- T026, T027 (Phase 3) — en paralelo entre sí, después de T019
- T029, T030, T031, T032 (Phase 4) — en paralelo después de T028
- T033, T034 (Phase 4) — en paralelo
- T036, T037 (Phase 5) — en paralelo después de T035
- T039–T045 (Phase 6) — todos en paralelo excepto T038 que va primero

---

## Parallel Example: User Story 1

```bash
# Después de T018 (apps.py), lanzar en paralelo:
Task T019: "Crear accounts/views.py con HealthView + ProfileView"
# Luego en paralelo:
Task T020: "Crear accounts/urls.py"
Task T023: "Crear portal/templates/portal/home.html"
Task T024: "Crear portal/templates/portal/access_denied.html"
# Luego tests (dependen de T019-T024):
Task T025: "Crear accounts/tests/test_views.py"
Task T026: "Crear accounts/tests/test_models.py"
Task T027: "Crear accounts/tests/test_backends.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (**CRÍTICO** — bloquea todo)
3. Completar Phase 3: User Story 1
4. **PARAR Y VALIDAR**: Quickstart Scenarios 1 + 2 pasan
5. D3 es funcional para autenticación — demo posible

### Incremental Delivery

1. Setup + Foundational → Stack D3 levanta
2. + US1 → Login funciona, `can-login` gateado → **MVP**
3. + US2 → 3 rutas protegidas por grupo funcionan
4. + US3 → Logout completo
5. + Polish → Validación end-to-end, no-regresión

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes — pueden correr en paralelo
- [Story] mapea la tarea a la user story para trazabilidad
- Cada user story es completable y testeable independientemente
- `docker compose down --volumes` es necesario cuando se modifica `realm-export.json` (reimporta realm)
- El secret de `d3-client` en `realm-export.json` debe ser valor literal, no `**********`
- Los grupos de Keycloak deben tener el scope `groups` asignado a `d3-client` para que aparezcan en el token
- Confirmar con `pytest` dentro del contenedor D3 antes de marcar Phase 6 completa
