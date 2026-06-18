# Contract: D1 Admin API (JSON Endpoints)

**Service**: D1 (main web app)
**Base URL**: `http://localhost:8001` (development)
**Auth mechanism**: Django session (OIDC). All endpoints require an active OIDC session cookie.
**Content-Type**: `application/json` for all requests with a body.
**Response format**: JSON (`JsonResponse`). No DRF.

All Admin API endpoints call the Keycloak Admin REST API via `kc_admin/client.py`. Errors from Keycloak are mapped to appropriate HTTP status codes.

---

## Authentication

All endpoints reject unauthenticated requests with:
```json
HTTP 401
{"error": "Authentication required"}
```

---

## Endpoints

### `GET /api/users/`

List all users in the Keycloak `app-realm`.

**Request**: No body.

**Response 200**:
```json
{
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "jdoe",
      "email": "jdoe@example.com",
      "enabled": true,
      "roles": ["viewer"],
      "groups": ["team-a"]
    }
  ]
}
```

**Response 502** (Keycloak unreachable):
```json
{"error": "Unable to reach identity provider"}
```

---

### `POST /api/users/create/`

Create a new user in Keycloak `app-realm`.

**Request body**:
```json
{
  "email": "newuser@example.com",
  "username": "newuser",
  "first_name": "New",
  "last_name": "User"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `email` | Yes | Valid email address |
| `username` | Yes | Unique username in realm |
| `first_name` | No | First name |
| `last_name` | No | Last name |

**Response 201**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "email": "newuser@example.com",
  "username": "newuser"
}
```

**Response 400** (missing required fields):
```json
{"error": "Fields required: email, username"}
```

**Response 409** (username or email already exists):
```json
{"error": "User with this username or email already exists"}
```

**Response 502** (Keycloak unreachable):
```json
{"error": "Unable to reach identity provider"}
```

---

### `POST /api/users/<sub>/roles/assign/`

Assign a realm role to an existing Keycloak user.

**Path param**: `sub` — Keycloak user UUID.

**Request body**:
```json
{
  "role_name": "admin"
}
```

**Response 200**:
```json
{"success": true, "user_id": "<sub>", "role": "admin"}
```

**Response 400** (missing `role_name`):
```json
{"error": "Field required: role_name"}
```

**Response 404** (user or role not found):
```json
{"error": "User or role not found"}
```

**Response 502** (Keycloak unreachable):
```json
{"error": "Unable to reach identity provider"}
```

---

### `POST /api/users/<sub>/groups/assign/`

Add an existing Keycloak user to a group.

**Path param**: `sub` — Keycloak user UUID.

**Request body**:
```json
{
  "group_name": "team-a"
}
```

**Response 200**:
```json
{"success": true, "user_id": "<sub>", "group": "team-a"}
```

**Response 400** (missing `group_name`):
```json
{"error": "Field required: group_name"}
```

**Response 404** (user or group not found):
```json
{"error": "User or group not found"}
```

**Response 502** (Keycloak unreachable):
```json
{"error": "Unable to reach identity provider"}
```

---

### `POST /api/users/<sub>/deactivate/`

Disable a Keycloak user. The user will be unable to log in until re-enabled in Keycloak.

**Path param**: `sub` — Keycloak user UUID.

**Request body**: None required.

**Response 200**:
```json
{"success": true, "user_id": "<sub>", "enabled": false}
```

**Response 404** (user not found):
```json
{"error": "User not found"}
```

**Response 409** (attempting to deactivate currently authenticated user):
```json
{"error": "Cannot deactivate your own account"}
```

**Response 502** (Keycloak unreachable):
```json
{"error": "Unable to reach identity provider"}
```

---

## Error Codes Summary

| HTTP Status | Meaning |
|-------------|---------|
| 200 | Success |
| 201 | Resource created |
| 400 | Missing or invalid request fields |
| 401 | Not authenticated (no OIDC session) |
| 404 | Keycloak user, role, or group not found |
| 405 | Method not allowed |
| 409 | Conflict (duplicate user, self-deactivation) |
| 502 | Keycloak Admin API unreachable or returned an error |

---

## Implementation Notes

- All endpoints are plain Django views returning `JsonResponse`. No DRF serializers.
- All Keycloak calls go through `d1/kc_admin/client.py` functions — views never call `KeycloakAdmin` directly.
- Structured log entries are written for every Admin API call: `user_id`, `action`, `target_sub`, `result`, `duration_ms`.
- Keycloak `KeycloakError` exceptions are caught in `client.py` and re-raised as typed exceptions that views map to HTTP status codes.
