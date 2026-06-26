# Quickstart: D2 Split Authentication Validation

**Feature**: `004-d2-split-auth`
**Date**: 2026-06-19

This guide covers how to set up the environment and validate all three user stories
from the spec end-to-end.

---

## Prerequisites

1. Docker and Docker Compose installed and running.
2. `.env` file updated with the new SMTP variables (see Setup §1).
3. Two test users created in Keycloak with the correct client roles (see Setup §2).
4. Mailtrap inbox access (https://mailtrap.io → Sandbox inbox → `d2` project).

---

## Setup

### 1. Add SMTP variables to `.env`

```bash
# In keycloak-django-sso/.env
SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=587
SMTP_FROM=noreply@d2.local
SMTP_USER=c972a560fc43ca
SMTP_PASSWORD=292abebd9c93c9
```

Add the same variables to the `keycloak:` service `environment:` block in `docker-compose.yml`:
```yaml
environment:
  # ... existing vars ...
  SMTP_HOST: ${SMTP_HOST}
  SMTP_PORT: ${SMTP_PORT}
  SMTP_FROM: ${SMTP_FROM}
  SMTP_USER: ${SMTP_USER}
  SMTP_PASSWORD: ${SMTP_PASSWORD}
```

### 2. Build and start the stack

```bash
cd keycloak-django-sso
docker compose down --volumes   # clean state
docker compose build keycloak   # builds extended image with magic-link JAR
docker compose up -d
```

Wait for Keycloak to be healthy:
```bash
docker compose logs keycloak -f | grep "Keycloak.*started"
```

### 3. Create test users in Keycloak

Navigate to `http://localhost:8080` → Administration Console → `app-realm`.

**User A — password flow**:
- Username: `d2_form_user`
- Email: any valid Mailtrap address (e.g. `d2_form_user@d2.local`)
- Email Verified: ON
- Set a known password (Credentials tab)
- Groups: none required for this feature
- Roles → Client Roles → `d2-client` → assign `login_form`

**User B — magic link flow**:
- Username: `d2_magic_user`
- Email: any valid Mailtrap address (e.g. `d2_magic_user@d2.local`)
- Email Verified: ON
- No password needed
- Roles → Client Roles → `d2-client` → assign `auto_login`

---

## Scenario 1: Password Flow (US1 — P1)

**What this validates**: User with `login_form` role sees a password prompt after username entry.

**Steps**:

1. Open an incognito/private browser window.
2. Navigate to `http://localhost:8002/`.
3. **Expected**: Redirected to Keycloak → screen shows only a **username/email field** (no password field visible).
4. Enter `d2_form_user` and press Continue.
5. **Expected**: Screen now shows a **password field** (not an email notification).
6. Enter the correct password.
7. **Expected**: Redirected to `http://localhost:8002/` — authenticated, D2 home page shown.

**Negative test — wrong password**:

Repeat steps 1–4, then enter a wrong password.
- **Expected**: Authentication error message. No D2 access granted. Username field is present for retry.

---

## Scenario 2: Magic Link Flow (US2 — P2)

**What this validates**: User with `auto_login` role receives a magic link email and can authenticate by clicking it.

**Steps**:

1. Open Mailtrap → Sandbox → check that the inbox for `c972a560fc43ca` is visible and empty (or note existing emails).
2. Open an incognito/private browser window.
3. Navigate to `http://localhost:8002/`.
4. **Expected**: Redirected to Keycloak → screen shows only a **username/email field**.
5. Enter `d2_magic_user` and press Continue.
6. **Expected**: Screen shows an **informational message** ("A login link has been sent to your email" or similar). **No password field**.
7. Switch to Mailtrap. Within 30 seconds a new email should appear.
8. Open the email. Click the magic link.
   > **Note**: The link can be clicked in any browser context — the same incognito window,
   > a new tab, or a completely different regular browser window. D2 handles cross-context
   > magic link callbacks automatically (see `research.md §7`).
9. **Expected**: Browser redirects to `http://localhost:8002/` — authenticated, D2 home page shown.

**Negative test — expired link**:

Repeat steps 2–7. Do NOT click the link immediately. After 1 hour (or reduce `expirationInSeconds` in config to 60 for testing), click the link.
- **Expected**: Keycloak shows an error ("Link expired" or similar). No D2 access.

**Negative test — used link**:

Repeat steps 2–9 (successful login). Then click the same magic link URL again (from browser history or Mailtrap).
- **Expected**: Keycloak shows an error ("Link already used" or similar). No second session.

---

## Scenario 3: Session Expiration (US3 — P3)

**What this validates**: D2 sessions expire at or around the 8-hour mark and force full re-login.

> For practical testing, temporarily reduce session lifetimes.

**Temporary config for testing** (revert after):

In `realm-export.json` → `d2-client.attributes`:
```json
"client.session.max.lifespan": "120"   // 2 minutes for testing
```

In `d2/config/settings/base.py`:
```python
SESSION_COOKIE_AGE = 120
OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS = 60   # check every 60 seconds
```

Rebuild D2 and restart:
```bash
docker compose restart d2
```

**Steps**:

1. Log in to D2 as `d2_form_user` (Scenario 1 steps 1–7).
2. Verify you are on the D2 home page (authenticated).
3. Wait 2 minutes and refresh the page (or navigate to any protected D2 page).
4. **Expected**: Redirected to Keycloak login screen (full flow from username entry).
5. Log in again as `d2_form_user`.
6. **Expected**: Fresh D2 session established. D2 home page shown again.

**Verification that expiry is absolute (not sliding)**:

1. Log in to D2.
2. Navigate between D2 pages every 30 seconds for 90 seconds (3 requests within the 2-minute window).
3. At 2 minutes, make one more request.
4. **Expected**: Redirected to login — confirms expiry is from login time, not from last activity.

---

## Scenario 4: Access Control — User With No Role (Edge Case)

**What this validates**: Users without `login_form` or `auto_login` role cannot authenticate.

**Steps**:

1. Create a test user in Keycloak with NO client roles on `d2-client` (no `login_form`, no `auto_login`).
2. Open incognito window → navigate to `http://localhost:8002/`.
3. Enter the username on the Keycloak login screen.
4. **Expected**: Authentication error — Keycloak shows an error (no branch matched). No D2 access.

---

## Scenario 5: D1 Isolation Check

**What this validates**: D1 authentication is completely unaffected.

**Steps**:

1. Open incognito window → navigate to `http://localhost:8001/` (D1).
2. Log in with any valid D1 user (e.g. `d1_user_rrhh`).
3. **Expected**: D1 login flow is the same as before — standard Keycloak username+password screen (not identity-first, not magic link). D1 access granted normally.
4. Verify D1 session still works normally after this feature is deployed.

---

## Keycloak Logs for Debugging

```bash
# Check for authentication flow errors
docker compose logs keycloak 2>&1 | grep -i "error\|exception\|flow\|magic"

# Check for SMTP/email errors
docker compose logs keycloak 2>&1 | grep -i "smtp\|mail\|KC-SERVICES"

# Check magic-link provider loaded correctly
docker compose logs keycloak 2>&1 | grep -i "magic\|p2-inc\|provider"
```

---

## Expected State After Full Deployment

| Check | Expected |
|---|---|
| `http://localhost:8002/` (no session) | Redirects to Keycloak |
| Keycloak login for D2 — first screen | Username field only (no password) |
| `d2_form_user` → Continue | Password field appears |
| `d2_magic_user` → Continue | Informational screen + email sent |
| Magic link clicked (valid, unused) | D2 home page (authenticated) |
| Magic link clicked again | Keycloak error |
| `http://localhost:8001/` (D1) | Standard username+password Keycloak screen — unchanged |
| Session after 8h (production) | Forced re-login |
