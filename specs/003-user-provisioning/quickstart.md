# Quickstart: User Provisioning Validation

**Feature**: [spec.md](spec.md) | **Date**: 2026-06-18

---

## Prerequisites

1. Stack running: `docker compose up` from `keycloak-django-sso/`
2. Keycloak SMTP configured (or use the Keycloak dev email catch — see note below)
3. A user with `d1:admin` group exists and can log into D1 (e.g. `d1_user_admin`)
4. D1 accessible at `http://localhost:8001`

> **SMTP note**: For local dev, configure Keycloak's email settings to point to a local mail catcher (e.g. MailHog on port 1025). Without SMTP, the activation email step will fail gracefully (Scenario 3 below tests this).

---

## Scenario 1 — Happy path: create user + receive activation email

**Goal**: Verify US1 (P1) end-to-end.

1. Log into D1 as `d1_user_admin` → navigate to `http://localhost:8001/provision/`
2. Fill in:
   - Username: `testuser_new`
   - Email: `testuser_new@example.com`
   - First name: `Test` (optional)
   - Groups: check `d1:worker`
   - Role: leave empty or pick any realm role
3. Submit the form
4. **Expected**: Green success message containing `testuser_new@example.com`
5. Verify in Keycloak Admin at `http://localhost:8080` → Users → find `testuser_new`:
   - Enabled: ON
   - Email verified: OFF
   - Required actions: `UPDATE_PASSWORD`, `UPDATE_PROFILE`
   - Groups: `d1:worker`
6. Open mail catcher → find activation email → click the link → complete profile + set password
7. Log into D1 as `testuser_new` → verify access to `/worker/` (200) and `/rrhh/` (access denied)

---

## Scenario 2 — Duplicate user error

**Goal**: Verify US2 — form retains values on conflict.

1. Log into D1 as `d1_user_admin` → navigate to `/provision/`
2. Fill form with `username=d1_user_admin` (or any existing Keycloak username) and a fresh email
3. Submit
4. **Expected**:
   - Form re-renders with an inline error message identifying the duplicate
   - All other form fields retain their entered values
   - No new user appears in Keycloak
5. Fix the username to something unique → resubmit → expect success (Scenario 1 outcome)

---

## Scenario 3 — Partial success: email fails

**Goal**: Verify US3 — user is created even when email cannot be sent.

1. Temporarily disable SMTP in Keycloak (or remove SMTP host setting)
2. Log into D1 as `d1_user_admin` → navigate to `/provision/`
3. Fill form with fresh username and email → submit
4. **Expected**:
   - Yellow **warning** message (not red error) indicating email failed
   - The username mentioned in the warning matches the created user
5. Verify in Keycloak Admin → user exists with groups/role assigned
6. Re-enable SMTP

---

## Scenario 4 — Access control

**Goal**: Verify FR-001 — only `d1:admin` users can reach `/provision/`.

1. Log into D1 as a user with only `d1:rrhh` group
2. Navigate to `http://localhost:8001/provision/`
3. **Expected**: Redirect to `/access-denied/?required=d1:admin`

4. Log out → navigate to `http://localhost:8001/provision/` without a session
5. **Expected**: Redirect to `/oidc/authenticate/?next=/provision/`

---

## Scenario 5 — Group visual labels

**Goal**: Verify SC-004 — every group is labeled by application.

1. Log into D1 as `d1_user_admin` → navigate to `/provision/`
2. Inspect the group selection area
3. **Expected**: Each of the 6 groups has a visible label indicating D1 or D2 (e.g. "D1 — Worker", "D2 — Editor")
4. No group is listed without a label

---

## Verification checklist

- [ ] `/provision/` returns 200 for `d1:admin` user
- [ ] `/provision/` redirects unauthenticated user to OIDC login
- [ ] `/provision/` redirects non-admin authenticated user to access-denied
- [ ] Form submission creates user in Keycloak with `emailVerified=false` and required actions
- [ ] Group selection assigns correct groups in Keycloak
- [ ] Activation email arrives after form submission (with SMTP configured)
- [ ] Duplicate username/email → inline form error, field values retained
- [ ] Email failure → warning shown, user not deleted
- [ ] Activated user can log into D1 or D2 per assigned groups
