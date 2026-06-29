# Data Model: D3 Django Service

**Feature**: D3 Django Service  
**Date**: 2026-06-26  

---

## Django Entities

### UserProfile

Almacena el estado sincronizado del usuario de Keycloak en D3. Misma estructura que D1.

| Campo | Tipo | Descripción |
|---|---|---|
| `user` | OneToOneField → `auth.User` | Usuario Django asociado (username = Keycloak `sub`) |
| `sub` | CharField(255) unique | Keycloak subject identifier |
| `email` | EmailField | Email del usuario desde claims |
| `roles` | JSONField | Roles del cliente `d3-client` (sincronizados al login) |
| `groups` | JSONField | Grupos `d3:*` sincronizados desde Keycloak |
| `last_synced_at` | DateTimeField | Timestamp del último sync exitoso |

**Django groups** (`auth_group`): Los grupos de Django (`d3:normas`, `d3:documentos`, `d3:leyes`) se sincronizan desde Keycloak vía `D3KeycloakOIDCBackend.update_user()`. Son los que comprueba `require_groups`.

---

## Keycloak Entities

### Realm: `app-realm` (existente — sin cambios estructurales)

#### Grupos nuevos

```json
[
  {
    "id": "4b6bb533-8d9b-4efc-9a9a-947dba43008e",
    "name": "d3:normas",
    "path": "/d3:normas",
    "subGroups": []
  },
  {
    "id": "50f027a2-cfdf-43f4-a4d3-e40973f060e6",
    "name": "d3:documentos",
    "path": "/d3:documentos",
    "subGroups": []
  },
  {
    "id": "22d0de0c-244d-4234-924b-6071095867d4",
    "name": "d3:leyes",
    "path": "/d3:leyes",
    "subGroups": []
  }
]
```

Añadir a la lista `groups` del realm-export.json.

#### Cliente `d3-client`

```json
{
  "id": "5ab2ed9f-631d-4c1d-a0a9-a29f8098f800",
  "clientId": "d3-client",
  "name": "D3 Client",
  "enabled": true,
  "publicClient": false,
  "standardFlowEnabled": true,
  "directAccessGrantsEnabled": false,
  "serviceAccountsEnabled": false,
  "secret": "<literal-value-matching-D3_OIDC_CLIENT_SECRET>",
  "redirectUris": ["http://localhost:8003/oidc/callback/*"],
  "webOrigins": ["http://localhost:8003"],
  "attributes": {
    "post.logout.redirect.uris": "http://localhost:8003/"
  },
  "authenticationFlowBindingOverrides": {
    "browser": "a14bbbc7-d1e3-4e68-8287-ca9f8fa1f3dc"
  },
  "defaultClientScopes": [
    "web-origins", "acr", "profile", "roles", "email", "groups"
  ],
  "optionalClientScopes": [
    "address", "phone", "offline_access", "microprofile-jwt"
  ]
}
```

Añadir a la lista `clients` del realm-export.json.

#### Rol `can-login` en `d3-client`

```json
{
  "roles": {
    "client": {
      "d3-client": [
        {
          "id": "aedb30ec-1d87-43a5-ac4d-4ba0aaeee665",
          "name": "can-login",
          "description": "Permite al usuario acceder a D3",
          "composite": false,
          "clientRole": true,
          "containerId": "5ab2ed9f-631d-4c1d-a0a9-a29f8098f800"
        }
      ]
    }
  }
}
```

Añadir la entrada `d3-client` en `roles.client` del realm-export.json.

#### AuthenticatorConfig `d3-client-role-cfg`

```json
{
  "id": "f63ed07c-7cf5-4ba1-b2de-4fc19614e8c6",
  "alias": "d3-client-role-cfg",
  "config": {
    "condUserRole": "d3-client.can-login",
    "negate": "true"
  }
}
```

Añadir a la lista `authenticatorConfig` del realm-export.json.

---

## Keycloak Authentication Flow: D3 Browser Flow

El flujo de D3 es una copia del D1 Browser Flow, renombrando todo de `d1-*` a `d3-*`.

### Estructura jerárquica

```text
D3 Browser Flow (id: a14bbbc7)  [BASIC_FLOW]
├── d3-client-auth-methods (id: 4b6c98f7)  [BASIC_FLOW, prio=0, ALTERNATIVE]
│   ├── auth-cookie                         [REQUIRED, prio=0]
│   ├── auth-spnego                         [DISABLED, prio=1]
│   ├── identity-provider-redirector        [ALTERNATIVE, prio=2]
│   └── d3-client-forms (id: 031153f8)      [BASIC_FLOW, ALTERNATIVE, prio=3]
│       ├── auth-username-password-form     [REQUIRED, prio=0]
│       └── d3-client-otp (id: db9b4017)   [CONDITIONAL, prio=1]
│           ├── condition-user-configured   [REQUIRED, prio=0]
│           └── auth-otp-form               [REQUIRED, prio=1]
└── d3-client-role-check (id: 7f892c3d)    [CONDITIONAL, prio=1]
    ├── conditional-user-role               [REQUIRED, prio=0]  ← cfg: d3-client-role-cfg
    └── deny-access-authenticator           [REQUIRED, prio=1]
```

**Diferencia clave vs D2**: `d3-client-role-check` está al TOP LEVEL del flujo (prio=1), no dentro de `d3-client-forms`. Esto es igual que D1.

**Diferencia clave vs D1**: `d3-client-forms` usa `auth-username-password-form` (formulario combinado), igual que D1.

### Fragmentos JSON para realm-export.json

#### Flujo raíz D3 Browser Flow

```json
{
  "id": "a14bbbc7-d1e3-4e68-8287-ca9f8fa1f3dc",
  "alias": "D3 Browser Flow",
  "description": "Browser flow for D3 with can-login role check",
  "providerId": "basic-flow",
  "topLevel": true,
  "builtIn": false,
  "authenticationExecutions": [
    {
      "authenticatorFlow": true,
      "requirement": "ALTERNATIVE",
      "priority": 0,
      "flowAlias": "d3-client-auth-methods",
      "userSetupAllowed": false,
      "autheticatorFlow": true
    },
    {
      "authenticatorFlow": true,
      "requirement": "CONDITIONAL",
      "priority": 1,
      "flowAlias": "d3-client-role-check",
      "userSetupAllowed": false,
      "autheticatorFlow": true
    }
  ]
}
```

#### Subflow: d3-client-auth-methods

```json
{
  "id": "4b6c98f7-8104-4fec-9ee6-e1a18eb3e592",
  "alias": "d3-client-auth-methods",
  "description": "D3 auth methods: cookie, spnego, IdP redirect, forms",
  "providerId": "basic-flow",
  "topLevel": false,
  "builtIn": false,
  "authenticationExecutions": [
    {
      "authenticator": "auth-cookie",
      "requirement": "ALTERNATIVE",
      "priority": 0,
      "userSetupAllowed": false,
      "autheticatorFlow": false
    },
    {
      "authenticator": "auth-spnego",
      "requirement": "DISABLED",
      "priority": 1,
      "userSetupAllowed": false,
      "autheticatorFlow": false
    },
    {
      "authenticator": "identity-provider-redirector",
      "requirement": "ALTERNATIVE",
      "priority": 2,
      "userSetupAllowed": false,
      "autheticatorFlow": false
    },
    {
      "authenticatorFlow": true,
      "requirement": "ALTERNATIVE",
      "priority": 3,
      "flowAlias": "d3-client-forms",
      "userSetupAllowed": false,
      "autheticatorFlow": true
    }
  ]
}
```

#### Subflow: d3-client-forms

```json
{
  "id": "031153f8-c752-428b-84c5-ad73feec1bb1",
  "alias": "d3-client-forms",
  "description": "Combined username+password form for D3",
  "providerId": "basic-flow",
  "topLevel": false,
  "builtIn": false,
  "authenticationExecutions": [
    {
      "authenticator": "auth-username-password-form",
      "requirement": "REQUIRED",
      "priority": 0,
      "userSetupAllowed": false,
      "autheticatorFlow": false
    },
    {
      "authenticatorFlow": true,
      "requirement": "CONDITIONAL",
      "priority": 1,
      "flowAlias": "d3-client-otp",
      "userSetupAllowed": false,
      "autheticatorFlow": true
    }
  ]
}
```

#### Subflow: d3-client-otp

```json
{
  "id": "db9b4017-0406-448c-aabe-0e7d83d1ef05",
  "alias": "d3-client-otp",
  "description": "D3 OTP conditional",
  "providerId": "basic-flow",
  "topLevel": false,
  "builtIn": false,
  "authenticationExecutions": [
    {
      "authenticator": "condition-user-configured",
      "requirement": "REQUIRED",
      "priority": 0,
      "userSetupAllowed": false,
      "autheticatorFlow": false
    },
    {
      "authenticator": "auth-otp-form",
      "requirement": "REQUIRED",
      "priority": 1,
      "userSetupAllowed": false,
      "autheticatorFlow": false
    }
  ]
}
```

#### Subflow: d3-client-role-check

```json
{
  "id": "7f892c3d-1f22-4c79-8932-b9030849109a",
  "alias": "d3-client-role-check",
  "description": "Denies access if user does not have d3-client.can-login",
  "providerId": "basic-flow",
  "topLevel": false,
  "builtIn": false,
  "authenticationExecutions": [
    {
      "authenticator": "conditional-user-role",
      "authenticatorConfig": "d3-client-role-cfg",
      "requirement": "REQUIRED",
      "priority": 0,
      "userSetupAllowed": false,
      "autheticatorFlow": false
    },
    {
      "authenticator": "deny-access-authenticator",
      "requirement": "REQUIRED",
      "priority": 1,
      "userSetupAllowed": false,
      "autheticatorFlow": false
    }
  ]
}
```

---

## Relaciones de entidades

```text
Keycloak realm (app-realm)
  └── d3-client
        └── role: can-login           ← gate de acceso al flujo
  └── groups
        ├── d3:normas                 ← habilita /normas/
        ├── d3:documentos             ← habilita /documentos/
        └── d3:leyes                  ← habilita /leyes/

D3 Django (PostgreSQL: d3_db)
  auth_user
    └── accounts_userprofile          ← sub, email, roles, groups (JSONField)
  auth_group
    ├── d3:normas                     ← sincronizado desde Keycloak
    ├── d3:documentos
    └── d3:leyes
  auth_user_groups                    ← many-to-many user ↔ group
```
