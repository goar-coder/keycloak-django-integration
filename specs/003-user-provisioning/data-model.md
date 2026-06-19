# Data Model: User Provisioning with Activation Email

**Feature**: [spec.md](spec.md) | **Date**: 2026-06-18

> No new database tables. This feature creates users in Keycloak only. The user will not appear in D1's local database until their first login (existing OIDC backend handles that).

---

## Form Input Model (transient — not persisted)

Represents data collected from the admin via the provision form. Lives only in memory during the request.

| Field | Required | Type | Validation | Notes |
|---|---|---|---|---|
| `username` | Yes | String | Non-empty, max 150 chars | Must be unique in Keycloak (409 on conflict) |
| `email` | Yes | String (email) | Valid email format | Must be unique in Keycloak (409 on conflict) |
| `first_name` | No | String | Max 150 chars | Pre-fills Keycloak profile; user must confirm via UPDATE_PROFILE |
| `last_name` | No | String | Max 150 chars | Pre-fills Keycloak profile; user must confirm via UPDATE_PROFILE |
| `groups` | No | List of strings | Each value in allowed group list | Zero or more selections |
| `role` | No | String | Value in realm roles list, or empty | Zero or one selection |

---

## Static Group Catalog

Fixed at design time. Not fetched from Keycloak. Each group maps to exactly one application scope.

| Group Name | Application Access | Display Label |
|---|---|---|
| `d1:rrhh` | D1 only | D1 — RRHH |
| `d1:worker` | D1 only | D1 — Worker |
| `d1:admin` | D1 only | D1 — Admin |
| `d2:viewer` | D2 only | D2 — Viewer |
| `d2:editor` | D2 only | D2 — Editor |
| `d2:admin` | D2 only | D2 — Admin |

---

## Outcome States

| State | Trigger | User created in Keycloak? | Message shown to admin |
|---|---|---|---|
| **Success** | All steps complete | Yes | Green success with email address |
| **Partial — email failed** | User + groups + role OK, email send failed | Yes | Yellow warning identifying partial success |
| **Partial — role failed** | User + groups OK, role assignment failed | Yes | Yellow warning; no role assigned |
| **Partial — group failed** | User created, one or more group assignments failed | Yes | Yellow warning; user exists but incomplete groups |
| **Duplicate error** | `username` or `email` already in Keycloak | No | Red inline form error; all field values retained |
| **Validation error** | Required field missing (client-side or server-side) | No | Red inline form error; all field values retained |

---

## Keycloak User Payload (sent by `provision_user`)

```
username:        <from form>
email:           <from form>
firstName:       <from form, may be empty>
lastName:        <from form, may be empty>
enabled:         true
emailVerified:   false
requiredActions: ["UPDATE_PASSWORD", "UPDATE_PROFILE"]
credentials:     []   (no password set)
```

---

## New `KeycloakAdminClient` Methods

### `provision_user(email, username, first_name='', last_name='') → str`

- Creates user in Keycloak with activation-gated settings
- Returns the new Keycloak user UUID (`sub`)
- Raises `DuplicateUser` on 409 conflict
- Raises `KeycloakConnectionError` on other errors

### `send_activation_email(user_id) → None`

- Triggers `execute-actions-email` for `UPDATE_PASSWORD` and `UPDATE_PROFILE`
- Raises `KeycloakConnectionError` on failure (caller decides whether to propagate or warn)
- Does not affect the user record if it fails
