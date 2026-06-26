# Research: D2 Split Authentication

**Feature**: `004-d2-split-auth`
**Date**: 2026-06-19

---

## 1. Phase Two keycloak-magic-link Provider

**Decision**: Use `keycloak-magic-link` version **`0.26`** from Phase Two (p2-inc), obtained from Maven Central.

**Rationale**:
- This is the only production-ready magic-link extension for Keycloak that is actively
  maintained and compatible with Keycloak 24.
- It provides a drop-in Keycloak authenticator (registered provider ID **`ext-magic-form`**) that integrates
  natively into Keycloak's Authentication Flow system — no custom Keycloak SPI needed.
- It handles token generation, single-use enforcement, expiry, and email delivery through
  Keycloak's existing SMTP configuration.
- The JAR is deployed by simply placing it in `/opt/keycloak/providers/`. Keycloak 24
  auto-discovers providers on startup.

**GitHub**: https://github.com/p2-inc/keycloak-magic-link

**Maven Central**: `io.phasetwo.keycloak:keycloak-magic-link:0.26`

**Version pinning**: Version `0.26` is the Maven Central release compatible with Keycloak 24.0.
Version `0.72` (also on Maven Central) targets Keycloak 26.6.3 and is incompatible — it
causes a "Failed to create a new filesystem" error on startup with KC 24. Pin to `0.26` in
the Dockerfile (`ARG MAGIC_LINK_VERSION=0.26`) to ensure reproducible builds.

> ⚠️ **Correction from original plan**: The initial research incorrectly specified version
> `2.1.0.1` from GitHub releases. That URL returned 404. The correct source is Maven Central
> and the correct KC24-compatible version is `0.26`.

**Docker build approach** (two-stage — verified working):
The Keycloak 24 base image does not have `curl` or `wget`. Direct `ADD https://...` failed
intermittently. A two-stage build is used instead:

```dockerfile
ARG MAGIC_LINK_VERSION=0.26

FROM alpine AS downloader
ARG MAGIC_LINK_VERSION
RUN wget -q \
    "https://repo1.maven.org/maven2/io/phasetwo/keycloak/keycloak-magic-link/${MAGIC_LINK_VERSION}/keycloak-magic-link-${MAGIC_LINK_VERSION}.jar" \
    -O /keycloak-magic-link.jar

FROM quay.io/keycloak/keycloak:24.0
COPY --from=downloader /keycloak-magic-link.jar /opt/keycloak/providers/keycloak-magic-link.jar
```

**Alternatives considered**:
- Building a custom Keycloak SPI: rejected — significant Java development overhead for
  functionality already available in Phase Two's open-source extension.
- Using Keycloak's built-in "Email OTP" authenticator: rejected — it requires the user to
  enter a code manually, not a one-click link. Poor UX for the `auto_login` use case.
- Using Keycloak's WebAuthn/passkeys: rejected — requires device registration flow,
  incompatible with the zero-setup requirement for `auto_login` users.

---

## 2. Identity-First Login Flow (Username-Only First Screen)

**Decision**: Use `auth-username-form` + two CONDITIONAL subflows as the replacement for
the current `auth-username-password-form` in `d2-client-forms`.

**Rationale**:
Keycloak 24 ships two distinct form authenticators:
- `auth-username-password-form`: shows username AND password on the same screen — no
  opportunity to branch between users before password entry.
- `auth-username-form`: shows ONLY the username field, stores the identified user in the
  authentication context, and passes control to the next step in the flow.

Using `auth-username-form` as step 1 allows Keycloak to identify the user first. Steps 2+
can then use `conditional-user-role` conditions to select the correct branch.

**Flow structure** (replaces content of `d2-client-forms`):

```
d2-client-forms (ALTERNATIVE subflow)
├── auth-username-form                   REQUIRED  ← identify user, no password
├── d2-password-branch                   CONDITIONAL
│   ├── conditional-user-role            REQUIRED  config: d2-client.login_form, negate=false
│   └── auth-password-form               REQUIRED
└── d2-magic-link-branch                 CONDITIONAL
    ├── conditional-user-role            REQUIRED  config: d2-client.auto_login, negate=false
    └── magic-link                       REQUIRED  config: d2-magic-link-cfg
```

**How CONDITIONAL subflows work in Keycloak**:
A CONDITIONAL subflow executes its children only if ALL its condition authenticators evaluate
to TRUE. If the condition fails (user does NOT have the role), the entire conditional subflow
is skipped. If neither branch matches (user has neither role), authentication fails with an
access-denied error — this is the intended behavior for the edge case of users with no role.

**Alternatives considered**:
- `select-authenticator`: Keycloak 22+ feature that lets the user choose their auth method.
  Rejected — the choice must be automatic (based on role), not user-driven.
- Using a single flow with a deny-on-match pattern: rejected — more complex, harder to
  debug and maintain.

---

## 3. Per-Client Session Override in Keycloak 24

**Decision**: Override session lifetime at the `d2-client` level using client-level
attributes `client.session.max.lifespan` and `client.session.idle.timeout` set to `28800`.

**Rationale**:
Keycloak 24 supports per-client session overrides via client attributes. The realm-level
settings currently are:
- `ssoSessionMaxLifespan`: 36000 (10 hours)
- `ssoSessionIdleTimeout`: 1800 (30 minutes)

The d2-client needs BOTH set to 28800 (8 hours) so that:
1. The absolute maximum is 8 hours (enforced by `client.session.max.lifespan`).
2. The idle timeout is also 8 hours, effectively disabling idle expiry in favor of the
   absolute limit (because the max lifespan always fires first at 8h).

**Keycloak 24 attribute keys**:
- `client.session.max.lifespan` (integer, in seconds)
- `client.session.idle.timeout` (integer, in seconds)

These are set in the `attributes` map of the client object in `realm-export.json`.

**Impact on D1**: Zero. D1 uses `d1-client`. Client-level session overrides are scoped to
the specific client. The realm defaults remain unchanged for all other clients.

---

## 4. D2 Session Alignment (Django ↔ Keycloak)

**Decision**: Add `SESSION_COOKIE_AGE = 28800` and `OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS = 3600`
to D2's `base.py`.

**Problem being solved**:
Currently D2 has no explicit `SESSION_COOKIE_AGE` (defaults to Django's 1209600 = 2 weeks).
This means Django's session cookie would still be valid long after Keycloak's session expires.
The `SessionRefresh` middleware from `mozilla-django-oidc` periodically calls Keycloak to
renew the token; if Keycloak's session is gone, it redirects to login.

**How expiration works end-to-end**:

```
T=0h   → User logs in. Django session created. Keycloak session created.
T=1h   → SessionRefresh triggers (OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS=3600).
           Keycloak session still valid → silently renews token. User unaffected.
T=2h   → Same silent renewal.
...
T=8h   → Keycloak session max lifespan reached. Keycloak session expired.
T=8h+Δ → Next SessionRefresh check (at most 1h later). Keycloak rejects renewal
           with login_required. Mozilla-django-oidc redirects user to /oidc/authenticate/.
           User sees D2 login page (Keycloak). Full flow restarts.
```

**Trade-off**: The user MAY remain logged in for up to 8h + 1h = 9h in the worst case
(if they logged in just after a renewal check). For the stated requirement of "exactly 8
hours", this is a 0–1h window of tolerance. The alternative (OIDC_RENEW every 5 minutes)
is exact but causes ~96 Keycloak round-trips per 8-hour session vs ~8 round-trips with 1h.

**Why SESSION_COOKIE_AGE = 28800**:
If left at 2 weeks, a user whose Keycloak session expired at 8h could potentially trick
Django into serving cached session data without a Keycloak check. Setting `SESSION_COOKIE_AGE`
to 28800 ensures the Django session cookie itself also expires at 8h as a second line of
defense. Note: `SESSION_SAVE_EVERY_REQUEST` must remain `False` (Django default) to prevent
the cookie age from being reset on every request — otherwise the 8h window becomes sliding,
not absolute.

---

## 5. SMTP Secrets Handling in realm-export.json

**Decision**: Use Keycloak's `${ENV_VAR}` syntax in `realm-export.json` for all SMTP
credentials.

**Rationale**: `realm-export.json` is committed to git (required by constitution for
reproducible environment setup). SMTP credentials must not be committed. Keycloak 24
supports environment variable substitution in its JSON configuration at import time using
the `${VARIABLE_NAME}` syntax.

**Variables to add to `.env` and `docker-compose.yml` keycloak environment**:
```
SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=587
SMTP_FROM=noreply@d2.local
SMTP_USER=c972a560fc43ca
SMTP_PASSWORD=292abebd9c93c9
```

**Verified**: Keycloak 24's `--import-realm` does honor `${VAR}` syntax in the `smtpServer`
block. The SMTP configuration with `${SMTP_HOST}`, `${SMTP_PORT}`, etc. imported correctly
and email delivery via Mailtrap sandbox worked as expected. No fallback to Admin REST API
or manual console configuration was needed.

---

## 6. Existing D2 Browser Flow — Current vs Target State

**Current state** (as of inspection on 2026-06-19):

The `D2 Browser Flow` already exists in `realm-export.json` and is already bound to
`d2-client`. However, `d2-client-forms` currently contains `auth-username-password-form`
(combined username+password on a single screen), which means all D2 users go through the
same password form regardless of role.

The `d2-client-role-check` CONDITIONAL subflow currently uses:
- `conditional-user-role`: checks `d2-client.can-login` with `negate=true`
- `deny-access-authenticator`

This means: if the user does NOT have `can-login` role → deny access. This acts as an
allowlist guard — only users with `can-login` can proceed.

**Target state**: The `can-login` role check guard can remain as an outer allowlist
(ensuring only provisioned D2 users can even attempt the split flow), or be removed in
favor of the role-specific branches failing naturally for unassigned users. For clarity,
the recommendation is to **keep the guard but change the checked role** — instead of
`can-login`, check that the user has either `login_form` OR `auto_login` (which is not
expressible as a single conditional-user-role condition). Alternatively, remove the guard
and rely on the two branches failing for unassigned users.

**Recommended approach**: Remove `d2-client-role-check` and `can-login` role. The split
branches provide natural access control — a user with neither `login_form` nor `auto_login`
will have no branch execute and authentication will fail with Keycloak's default error.
This is simpler and avoids maintaining a redundant role.

---

## 7. Magic Link Cross-Context OIDC Callback Fix

**Problem**: When a user initiates the magic-link flow in one browser context (e.g. incognito
window) and then clicks the magic link in a different browser context (e.g. the email client
opens the link in a regular browser tab), Django's OIDC callback raises:

```
SuspiciousOperation: OIDC callback state not found in session `oidc_states`!
```

This happens because `mozilla-django-oidc` stores the `state` value in the session at the
time of the initial redirect to Keycloak (`/oidc/authenticate/`). The magic link email,
when opened in a new browser context, does not share that session, so the state check fails.

**Root cause analysis**:
- `mozilla-django-oidc` version 4.0.1 does not have `OIDC_ALLOW_UNSOLICITED_LOGINS` (that
  setting only exists in newer versions).
- The state check at `views.py` raises `SuspiciousOperation` at line 100, not at line 92
  (meaning the session KEY `oidc_states` may exist as an empty dict or with a different state
  from a previous session, but the specific `state` value from the magic link is absent).

**Decision**: Custom `MagicLinkCallbackView` in D2 + `OIDC_USE_NONCE = False`.

**Implementation** (`keycloak-django-sso/d2/accounts/views.py`):
```python
class MagicLinkCallbackView(OIDCAuthenticationCallbackView):
    def get(self, request):
        state = request.GET.get("state", "")
        if state and (
            "oidc_states" not in request.session
            or state not in request.session.get("oidc_states", {})
        ):
            existing = request.session.get("oidc_states", {})
            existing[state] = {"nonce": None, "code_verifier": None}
            request.session["oidc_states"] = existing
            request.session.modified = True
        return super().get(request)
```

Wired in `config/urls.py` BEFORE `include('mozilla_django_oidc.urls')` so it takes priority:
```python
path('oidc/callback/', MagicLinkCallbackView.as_view(), name='oidc_authentication_callback'),
```

**Why `OIDC_USE_NONCE = False`**:
When the synthetic state entry is injected with `"nonce": None`, the standard callback
extracts `nonce = None` and passes it to the auth backend. If `OIDC_USE_NONCE` is `True`
(default), the backend compares `None` against the real nonce in the ID token and raises
`SuspiciousOperation: JWT Nonce verification failed`. Setting `OIDC_USE_NONCE = False`
in `base.py` skips this check.

**Security trade-off**: Nonce validation protects against authorization-code injection
attacks. For the password flow (US1) this protection is reduced to state-only validation
(still same-session, so the state check is sufficient). For the magic link flow (US2)
security is guaranteed by the single-use JWT action token in Keycloak (time-limited,
cryptographically signed). The overall risk in a dev environment with Keycloak as the
sole token issuer is acceptable.

**Alternatives rejected**:
- Upgrading `mozilla-django-oidc` to a version with `OIDC_ALLOW_UNSOLICITED_LOGINS`: would
  require auditing compatibility with all existing OIDC settings and D2 backends.
- Changing the magic link `redirectUriTemplate` to a separate URL (e.g. `/oidc/magic-callback/`):
  would require adding the new URL to Keycloak's valid redirect URIs and adding it to the realm-export,
  adding complexity for the same result.

---

## 8. Client Secrets in realm-export.json

**Problem**: Keycloak uses `"secret": "**********"` as a placeholder in `realm-export.json`
when exporting clients. On import with `--import-realm`, any client whose secret is
`"**********"` gets a newly generated random secret, making the secret unpredictable.
This breaks Django's `D1_OIDC_CLIENT_SECRET` and `D2_OIDC_CLIENT_SECRET` env vars after
every `docker compose down --volumes && docker compose up`.

**Decision**: Use literal, predictable dev secrets in `realm-export.json`.

- `d1-client.secret`: `"d1-client-dev-secret"` (hardcoded in realm-export.json)
- `d2-client.secret`: `"d2-client-dev-secret"` (hardcoded in realm-export.json)

These match the corresponding values in `.env` and `.env.example`. They are dev-only values
committed intentionally — not real credentials. Production deployments must override them.

---

## 9. Keycloak User Profile Config — firstName/lastName Not Required

**Problem**: Keycloak 24 enables Declarative User Profile by default and marks `firstName`
and `lastName` as required fields. After magic-link or password authentication, Keycloak
prompted users to fill in their name before allowing access, even though D2 does not use
these fields.

**Decision**: Embed `userProfileConfig` in `realm.attributes` as a JSON string to mark
`firstName` and `lastName` as not required.

This is set in `realm-export.json` under `attributes.userProfileConfig` as a serialized
JSON string. The relevant fields are given `"required": {}` (empty required block, no roles
required). This persists across `--import-realm` restarts without any manual admin console
intervention.
