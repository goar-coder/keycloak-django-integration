# Tasks: D2 Split Authentication

**Input**: Design documents from `specs/004-d2-split-auth/`

**References**: [spec.md](spec.md) | [plan.md](plan.md) | [data-model.md](data-model.md) | [research.md](research.md) | [quickstart.md](quickstart.md)

## Format: `[ID] [P?] [Story?] Description — file path`

- **[P]**: Can run in parallel (different files, no unresolved dependencies)
- **[Story]**: Which user story this task belongs to (US1/US2/US3)

---

## Phase 1: Setup

**Purpose**: Confirm current stack state before any changes.

- [x] T001 Verify baseline — confirm `keycloak:` service in `keycloak-django-sso/docker-compose.yml` still uses `image:` (not `build:`), confirm `keycloak/Dockerfile` does not exist, confirm no port conflicts on 8080/8001/8002 (`docker compose ps`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extended Keycloak image + new roles + SMTP — required before any user story can be tested.

**⚠️ CRITICAL**: All four editing tasks (T002–T005) can run in parallel since they touch different files. T006 must follow all of them.

- [x] T002 [P] Create `keycloak-django-sso/keycloak/Dockerfile` — contents: `FROM quay.io/keycloak/keycloak:24.0`; `ARG MAGIC_LINK_VERSION=2.1.0.1`; `ADD https://github.com/p2-inc/keycloak-magic-link/releases/download/${MAGIC_LINK_VERSION}/keycloak-magic-link-${MAGIC_LINK_VERSION}.jar /opt/keycloak/providers/keycloak-magic-link.jar` (verify release URL at https://github.com/p2-inc/keycloak-magic-link/releases before implementing)

- [x] T003 [P] Update `keycloak-django-sso/docker-compose.yml` — in the `keycloak:` service: replace `image: quay.io/keycloak/keycloak:24.0` with `build: {context: ./keycloak, dockerfile: Dockerfile}`; add env vars to the keycloak environment block: `SMTP_HOST: ${SMTP_HOST}`, `SMTP_PORT: ${SMTP_PORT}`, `SMTP_FROM: ${SMTP_FROM}`, `SMTP_USER: ${SMTP_USER}`, `SMTP_PASSWORD: ${SMTP_PASSWORD}`

- [x] T004 [P] Add SMTP credentials to `keycloak-django-sso/.env` — append: `SMTP_HOST=sandbox.smtp.mailtrap.io`, `SMTP_PORT=587`, `SMTP_FROM=noreply@d2.local`, `SMTP_USER=c972a560fc43ca`, `SMTP_PASSWORD=292abebd9c93c9`

- [x] T005 [P] Edit `keycloak-django-sso/keycloak/realm-export.json` — four changes in a single edit: (1) add `smtpServer` block at realm root level using `${SMTP_HOST}` etc. env var references (see data-model.md `smtpServer` fragment); (2) add `login_form` and `auto_login` objects to `roles.client.d2-client` array; (3) remove the `can-login` entry from `roles.client.d2-client`; (4) remove the `d2-client-role-check` entry from `authenticationFlows` array and remove its execution reference (the `flowAlias: "d2-client-role-check"` entry) from the `D2 Browser Flow` authenticationExecutions; also remove `d2-client-role-cfg` and `d2-client-role-config` from `authenticatorConfig` array

- [x] T006 Build extended Keycloak image and verify provider loads: run `docker compose build keycloak` from `keycloak-django-sso/`; then `docker compose down --volumes && docker compose up -d`; run `docker compose logs keycloak 2>&1 | grep -i "magic\|provider"` and confirm the magic-link provider appears; confirm no startup errors; confirm http://localhost:8080 is reachable

**Checkpoint**: Extended Keycloak image is running with magic-link provider, new roles exist in Keycloak, SMTP is configured.

---

## Phase 3: User Story 1 — Password Authentication for Form Users (Priority: P1) 🎯 MVP

**Goal**: Users with `login_form` role see a username-only screen first, then a password prompt. No magic link involved.

**Independent Test**: Create `d2_form_user` with `login_form` role → navigate to http://localhost:8002/ → verify username-only screen → enter username → verify password prompt appears (not email screen) → enter correct password → verify D2 access.

### Implementation for User Story 1

- [x] T007 [US1] Add authenticatorConfig entries to `keycloak-django-sso/keycloak/realm-export.json` — append three new entries to the `authenticatorConfig` array: (1) `d2-password-role-cfg` with `condUserRole: "d2-client.login_form"` and `negate: "false"`; (2) `d2-magic-role-cfg` with `condUserRole: "d2-client.auto_login"` and `negate: "false"`; (3) `d2-magic-link-cfg` with `expirationInSeconds: "3600"`, `singleUse: "true"`, `redirectUriTemplate: "http://localhost:8002/oidc/callback/"` — see data-model.md for complete JSON fragments

- [x] T008 [US1] Add new subflow definitions to `keycloak-django-sso/keycloak/realm-export.json` — append `d2-password-branch` and `d2-magic-link-branch` entries to the `authenticationFlows` array; `d2-password-branch` contains: `conditional-user-role` (REQUIRED, config=d2-password-role-cfg, priority=0) + `auth-password-form` (REQUIRED, priority=10); `d2-magic-link-branch` contains: `conditional-user-role` (REQUIRED, config=d2-magic-role-cfg, priority=0) + `magic-link` authenticator (REQUIRED, config=d2-magic-link-cfg, priority=10) — see data-model.md for complete JSON

- [x] T009 [US1] Update `d2-client-forms` subflow in `keycloak-django-sso/keycloak/realm-export.json` — replace the existing `auth-username-password-form` execution (and the `d2-client-otp` CONDITIONAL subflow reference) with three new executions: (1) `auth-username-form` REQUIRED priority=0 (identity-first: username only); (2) flowAlias `d2-password-branch` CONDITIONAL priority=10; (3) flowAlias `d2-magic-link-branch` CONDITIONAL priority=20

- [x] T010 [US1] Restart with clean volumes and validate US1: `docker compose down --volumes && docker compose up -d` from `keycloak-django-sso/`; then via Keycloak Admin Console (http://localhost:8080 → app-realm → Users) create user `d2_form_user` (email: d2_form_user@d2.local, email verified: ON, set password, client role: `login_form` on d2-client); open incognito browser to http://localhost:8002/ and execute quickstart.md Scenario 1 — verify username-only first screen, verify password prompt after username entry, verify D2 access after correct password; also test wrong password (verify error, no access)

**Checkpoint**: US1 fully functional — users with `login_form` role authenticate via username + password, two-screen flow works.

---

## Phase 4: User Story 2 — Magic Link Authentication for Auto-Login Users (Priority: P2)

**Goal**: Users with `auto_login` role see username screen, then informational screen with no password field, receive email with one-time magic link, click it, and access D2.

**Independent Test**: Create `d2_magic_user` with `auto_login` role → navigate to http://localhost:8002/ → enter username → verify no password prompt, informational screen shown → receive email in Mailtrap within 30s → click link → verify D2 access; reuse link → verify rejection.

### Implementation for User Story 2

*(The authentication flow is already fully configured in US1. US2 only requires the test user and validation.)*

- [x] T011 [US2] Create test user `d2_magic_user` via Keycloak Admin Console (http://localhost:8080 → app-realm → Users → Create): set email to `d2_magic_user@d2.local`, set Email Verified to ON, do NOT set any password, assign `auto_login` client role on d2-client; confirm user appears in the users list with no credentials set

- [x] T012 [US2] Validate US2 — execute quickstart.md Scenario 2: open Mailtrap inbox (note last email timestamp); open incognito browser to http://localhost:8002/; enter `d2_magic_user` on username screen; verify informational screen appears with no password field; check Mailtrap within 30 seconds for a new email from `noreply@d2.local`; click the magic link in the email; verify D2 home page loads (authenticated); then validate negative cases: copy the same link URL and open it again (verify Keycloak error — link already used); to test expiry, temporarily set `expirationInSeconds: "60"` in `d2-magic-link-cfg` in realm-export.json, restart with clean volumes, repeat flow without clicking for 1 min, click link, verify expiry error; restore `expirationInSeconds: "3600"` and restart clean again

**Checkpoint**: US2 fully functional — auto_login users receive magic link, link is single-use, expired links are rejected.

---

## Phase 5: User Story 3 — Absolute 8-Hour Session Expiration (Priority: P3)

**Goal**: D2 sessions expire at the 8-hour absolute mark (measured from login). Activity does not reset the timer. After expiry, user is redirected to full login flow.

**Independent Test**: Log in as `d2_form_user`, set session lifetime to 2 minutes for testing, wait 2 min + 1 OIDC renewal cycle, verify redirect to Keycloak; confirm expiry is from login time, not last activity.

### Implementation for User Story 3

- [x] T013 [P] [US3] Update d2-client `attributes` in `keycloak-django-sso/keycloak/realm-export.json` — add two entries to the existing `attributes` map on d2-client: `"client.session.max.lifespan": "28800"` and `"client.session.idle.timeout": "28800"` (8 hours in seconds)

- [x] T014 [P] [US3] Update `keycloak-django-sso/d2/config/settings/base.py` — add after the `SESSION_COOKIE_SAMESITE` line: `SESSION_COOKIE_AGE = 28800` (8 hours, prevents Django cookie outlasting Keycloak session) and `OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS = 3600` (SessionRefresh middleware checks with Keycloak every 1 hour)

- [x] T015 [US3] Apply US3 changes and validate: first set short test values — temporarily change `client.session.max.lifespan` to `"120"` in realm-export.json and `SESSION_COOKIE_AGE = 120`, `OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS = 60` in base.py; run `docker compose down --volumes && docker compose up -d` from `keycloak-django-sso/`; log in as `d2_form_user`; navigate D2 pages actively for 90 seconds to confirm no premature expiry; wait 2+ minutes; verify next D2 page request redirects to Keycloak login; log back in, confirm new session starts; then restore production values (`client.session.max.lifespan: "28800"`, `SESSION_COOKIE_AGE = 28800`, `OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS = 3600`) and restart clean

**Checkpoint**: US3 validated — D2 sessions have an absolute 8-hour lifetime enforced from Keycloak side, Django settings are aligned.

---

## Final Phase: Polish & End-to-End Validation

**Purpose**: Full scenario sweep, D1 isolation check, documentation.

- [x] T016 Execute quickstart.md Scenarios 4 and 5: create a user with NO d2-client roles, confirm they cannot authenticate to D2 (Scenario 4 — access control for no-role user); log in to D1 at http://localhost:8001/ with a D1 user, confirm standard username+password flow unchanged (Scenario 5 — D1 isolation); run D2 test suite: `docker compose exec d2 python -m pytest -v` and confirm all existing tests pass

- [x] T017 [P] Update `keycloak-django-sso/.env.example` to document the five new SMTP variables without values (SMTP_HOST=, SMTP_PORT=, SMTP_FROM=, SMTP_USER=, SMTP_PASSWORD=) with a comment indicating they are required for magic-link email delivery

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **blocks all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 complete
- **US2 (Phase 4)**: Depends on Phase 3 complete (realm-export.json changes from US1 include full flow structure)
- **US3 (Phase 5)**: Depends on Phase 2 complete (can run after US1 if parallel staffing)
- **Polish (Final Phase)**: Depends on all previous phases

### Within Phase 2

- T002, T003, T004, T005 are all parallel (different files: Dockerfile, docker-compose.yml, .env, realm-export.json)
- T006 must follow T002–T005

### Within Phase 3 (US1)

- T007 → T008 → T009 are sequential (all modify realm-export.json, each builds on previous)
- T010 must follow T009

### Within Phase 5 (US3)

- T013 [P] and T014 [P] are parallel (different files: realm-export.json and base.py)
- T015 must follow both T013 and T014

---

## Parallel Execution Examples

```bash
# Phase 2 — run simultaneously:
T002  Create keycloak/Dockerfile
T003  Update docker-compose.yml (build + SMTP env)
T004  Add SMTP vars to .env
T005  Edit realm-export.json (roles + SMTP block + remove can-login)

# Phase 5 (US3) — run simultaneously:
T013  Add session attributes to d2-client in realm-export.json
T014  Add SESSION_COOKIE_AGE + OIDC_RENEW to d2/config/settings/base.py
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Phase 1: Verify baseline (T001)
2. Phase 2: Build extended image + new roles + SMTP (T002–T006)
3. Phase 3: Identity-first flow + password branch (T007–T010)
4. **STOP**: Validate Scenario 1 from quickstart.md — password users can log in
5. Demonstrate: split auth routing works

### Incremental Delivery

1. After Phase 2: Extended Keycloak image running with magic-link provider
2. After Phase 3 (US1): Password-only users can authenticate via 2-screen flow
3. After Phase 4 (US2): Magic-link users receive email and authenticate without password
4. After Phase 5 (US3): Sessions expire at exactly 8 hours (within 1h tolerance)
5. After Final Phase: All 5 quickstart scenarios validated, D1 confirmed unaffected

---

## Notes

- Every `realm-export.json` change requires `docker compose down --volumes && docker compose up -d` to re-import the realm. There are THREE restart cycles in this plan: after T006 (Phase 2), after T010 (US1), and after T015 (US3/US2 combined final test).
- If `${VAR}` substitution does not work in the SMTP smtpServer block during `--import-realm`, configure SMTP via Keycloak Admin Console manually and re-export; see research.md §5.
- The `magic-link` authenticator provider ID must match exactly what Phase Two registers. Check Keycloak Admin Console → Authentication → search available authenticators after T006 to confirm the provider ID before writing T008.
- `auth-username-form` is the standard Keycloak 24 provider ID for identity-first username collection. Verify it appears in the authentication step picker after T006.
- D1 and d1-client are never touched. All changes are isolated to: `keycloak/Dockerfile`, `docker-compose.yml` (keycloak service only), `.env` (new SMTP vars), `realm-export.json` (d2-client and D2 flows), `d2/config/settings/base.py`.
