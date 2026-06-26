# Data Model: D2 Split Authentication

**Feature**: `004-d2-split-auth`
**Date**: 2026-06-19

> This feature introduces no new Django models and no new database tables.
> All persistent state lives in Keycloak (authentication flow config, sessions, magic-link tokens)
> and in Django's existing `django_session` table (OIDC token, session expiry).

---

## Entities

### 1. Authentication Flow (Keycloak — stored in `realm-export.json`)

Represents the full decision tree that runs when a D2 user attempts to log in.

| Field | Value | Notes |
|---|---|---|
| `alias` | `D2 Browser Flow` | Top-level flow name; already bound to d2-client |
| `providerId` | `basic-flow` | Standard Keycloak flow type |
| `topLevel` | `true` | Bound as browser flow override on d2-client |
| Binding | `d2-client.authenticationFlowBindingOverrides.browser` | Already set |

**Subflow hierarchy** (complete target state):

```
D2 Browser Flow                         topLevel=true
├── d2-client-auth-methods              REQUIRED
│   ├── auth-cookie                     ALTERNATIVE
│   ├── auth-spnego                     DISABLED
│   ├── identity-provider-redirector    ALTERNATIVE
│   └── d2-client-forms                 ALTERNATIVE
│       ├── auth-username-form          REQUIRED        ← identify user only
│       ├── d2-password-branch          CONDITIONAL
│       │   ├── conditional-user-role   REQUIRED        config: d2-magic-link-cfg → login_form
│       │   └── auth-password-form      REQUIRED
│       └── d2-magic-link-branch        CONDITIONAL
│           ├── conditional-user-role   REQUIRED        config: d2-magic-link-cfg → auto_login
│           └── ext-magic-form          REQUIRED        config: d2-magic-link-cfg
└── (d2-client-role-check removed — see research.md §6)
```

**State transitions for authentication**:

```
User visits D2 (no session)
        │
        ▼
[auth-cookie] ─── cookie valid ──────────────────────────→ D2 access granted
        │ no cookie
        ▼
[auth-username-form] ← user enters username
        │
        ├── user has login_form role
        │       ▼
        │   [auth-password-form] ← user enters password
        │       ├── correct → D2 access granted (8h session)
        │       └── wrong   → error, retry
        │
        ├── user has auto_login role
        │       ▼
        │   [magic-link] → email sent → informational screen shown
        │       └── user clicks link (within 1h, first use) → D2 access granted (8h session)
        │
        └── user has neither role → authentication error (no branch executes)
```

---

### 2. User Role Assignment (Keycloak — `realm-export.json`, `roles.client.d2-client`)

Each D2 user is assigned exactly one client-level role on `d2-client`.

| Role name | Description | Auth path triggered |
|---|---|---|
| `login_form` | Password-based authentication | `d2-password-branch` executes |
| `auto_login` | Magic-link passwordless authentication | `d2-magic-link-branch` executes |
| ~~`can-login`~~ | Legacy allowlist role | **Removed** — replaced by the two functional roles |

**Invariants**:
- Each user has exactly one of `login_form` or `auto_login`, never both.
- A user with neither role cannot authenticate to D2.
- Role assignment is managed in Keycloak (Admin Console or Admin REST API). D2 Django has no visibility into which role a user holds.

---

### 3. Magic Link Token (Keycloak — managed by Phase Two provider, in-memory/DB)

A short-lived, single-use credential sent by email when the `auto_login` branch executes.

| Attribute | Value | Source |
|---|---|---|
| Token format | Opaque URL token (UUID-style) | Phase Two provider |
| Delivery | Email to user's registered Keycloak email address | Via realm SMTP config |
| Expiry | 3600 seconds (1 hour) from generation | `d2-magic-link-cfg.expirationInSeconds` |
| Single-use | Yes — invalidated on first successful click | `d2-magic-link-cfg.singleUse=true` |
| Redirect target | `http://localhost:8002/oidc/callback/` | `d2-magic-link-cfg.redirectUriTemplate` |
| Storage | Keycloak internal (Infinispan cache / DB action token table) | Managed by provider |

**State transitions for Magic Link Token**:

```
[PENDING] → created when auto_login branch executes
    │
    ├── clicked within 1 hour (first use) → [CONSUMED] → user authenticated, token deleted
    ├── 1 hour elapsed without click       → [EXPIRED]  → token rejected on click, user sees error
    └── clicked after prior use            → [INVALID]  → token rejected, user sees error
```

---

### 4. D2 Session (Django `django_session` table + Keycloak SSO session)

A D2 session has two components that must be aligned:

| Component | Storage | Lifetime | Config |
|---|---|---|---|
| Django session cookie | Browser + `django_session` table | 8 hours | `SESSION_COOKIE_AGE = 28800` |
| Keycloak SSO session | Keycloak (DB/cache) | 8 hours absolute | `client.session.max.lifespan = 28800` on d2-client |
| OIDC token (in Django session) | `django_session` (serialized) | 8 hours | Driven by Keycloak SSO session expiry |

**Session expiry mechanism**:
1. At login, both Django session and Keycloak SSO session are created simultaneously.
2. Every `OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS` (3600s), `SessionRefresh` middleware checks with Keycloak.
3. Within 8h: Keycloak silently renews the token (SSO session valid). Django session is extended.
4. After 8h: Keycloak SSO session expired. Next renewal attempt returns `login_required`.
5. `SessionRefresh` redirects to `/oidc/authenticate/` → full authentication flow restarts.

**Key constraint**: `SESSION_SAVE_EVERY_REQUEST` must remain `False` (Django default).
If set to `True`, every page request would reset `SESSION_COOKIE_AGE` from the current time,
turning the 8h into a sliding window instead of absolute.

---

## SMTP Configuration Entity (Keycloak realm-level)

| Field | Value | Storage |
|---|---|---|
| `host` | `${SMTP_HOST}` → `sandbox.smtp.mailtrap.io` | `.env` |
| `port` | `${SMTP_PORT}` → `587` | `.env` |
| `from` | `${SMTP_FROM}` → `noreply@d2.local` | `.env` |
| `starttls` | `"true"` | `realm-export.json` (not secret) |
| `ssl` | `"false"` | `realm-export.json` (not secret) |
| `auth` | `"true"` | `realm-export.json` (not secret) |
| `user` | `${SMTP_USER}` | `.env` |
| `password` | `${SMTP_PASSWORD}` | `.env` |

SMTP config applies realm-wide. It is used by magic-link email delivery and by any other
Keycloak email (e.g., password reset for `login_form` users, if enabled in the future).

---

## Keycloak `realm-export.json` Changes — Full JSON Fragments

### New `smtpServer` block (realm root level)

```json
"smtpServer": {
  "host": "${SMTP_HOST}",
  "port": "${SMTP_PORT}",
  "from": "${SMTP_FROM}",
  "fromDisplayName": "D2 App",
  "auth": "true",
  "user": "${SMTP_USER}",
  "password": "${SMTP_PASSWORD}",
  "starttls": "true",
  "ssl": "false"
}
```

### New roles in `roles.client.d2-client`

```json
[
  {
    "id": "<generate-uuid>",
    "name": "login_form",
    "description": "Password-based authentication flow for D2",
    "composite": false,
    "clientRole": true,
    "containerId": "<d2-client-id>"
  },
  {
    "id": "<generate-uuid>",
    "name": "auto_login",
    "description": "Magic-link passwordless authentication flow for D2",
    "composite": false,
    "clientRole": true,
    "containerId": "<d2-client-id>"
  }
]
```

### New authenticatorConfig entries

```json
{
  "id": "<generate-uuid>",
  "alias": "d2-magic-link-cfg",
  "config": {
    "expirationInSeconds": "3600",
    "singleUse": "true",
    "sendEmailOnError": "false",
    "redirectUriTemplate": "http://localhost:8002/oidc/callback/"
  }
},
{
  "id": "<generate-uuid>",
  "alias": "d2-password-role-cfg",
  "config": {
    "condUserRole": "d2-client.login_form",
    "negate": "false"
  }
},
{
  "id": "<generate-uuid>",
  "alias": "d2-magic-role-cfg",
  "config": {
    "condUserRole": "d2-client.auto_login",
    "negate": "false"
  }
}
```

### Updated d2-client-forms (replaces existing content)

```json
{
  "id": "<existing-id-preserved>",
  "alias": "d2-client-forms",
  "providerId": "basic-flow",
  "topLevel": false,
  "builtIn": false,
  "authenticationExecutions": [
    {
      "authenticator": "auth-username-form",
      "requirement": "REQUIRED",
      "priority": 0,
      "authenticatorFlow": false
    },
    {
      "flowAlias": "d2-password-branch",
      "requirement": "CONDITIONAL",
      "priority": 10,
      "authenticatorFlow": true
    },
    {
      "flowAlias": "d2-magic-link-branch",
      "requirement": "CONDITIONAL",
      "priority": 20,
      "authenticatorFlow": true
    }
  ]
}
```

### New subflows

```json
{
  "alias": "d2-password-branch",
  "providerId": "basic-flow",
  "topLevel": false,
  "builtIn": false,
  "authenticationExecutions": [
    {
      "authenticator": "conditional-user-role",
      "authenticatorConfig": "d2-password-role-cfg",
      "requirement": "REQUIRED",
      "priority": 0
    },
    {
      "authenticator": "auth-password-form",
      "requirement": "REQUIRED",
      "priority": 10
    }
  ]
}
```

```json
{
  "alias": "d2-magic-link-branch",
  "providerId": "basic-flow",
  "topLevel": false,
  "builtIn": false,
  "authenticationExecutions": [
    {
      "authenticator": "conditional-user-role",
      "authenticatorConfig": "d2-magic-role-cfg",
      "requirement": "REQUIRED",
      "priority": 0
    },
    {
      "authenticator": "ext-magic-form",
      "authenticatorConfig": "d2-magic-link-cfg",
      "requirement": "REQUIRED",
      "priority": 10
    }
  ]
}
```

### d2-client session override (in client `attributes`)

```json
"attributes": {
  "post.logout.redirect.uris": "http://localhost:8002/##http://d2:8000/",
  "client.session.max.lifespan": "28800",
  "client.session.idle.timeout": "28800"
}
```
