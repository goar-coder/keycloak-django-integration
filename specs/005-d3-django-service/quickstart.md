# Quickstart Validation Guide: D3 Django Service

**Feature**: D3 Django Service  
**Date**: 2026-06-26  
**Prerequisites**: Docker, Docker Compose, `.env` file with `D3_*` variables  

---

## Prerequisites

### 1. Verify `.env` has D3 variables

```bash
grep D3 keycloak-django-sso/.env
```

Expected output includes:
```
D3_SECRET_KEY=<some-value>
D3_DB_PASSWORD=<some-value>
D3_OIDC_CLIENT_SECRET=<same-value-as-in-realm-export>
```

### 2. Start the stack

```bash
cd keycloak-django-sso
docker compose down --volumes   # clean start — reimports realm
docker compose up -d
```

### 3. Wait for services

```bash
docker compose ps
```

All services should be `healthy`. Keycloak takes ~60s on first start.

### 4. Verify D3 is running

```bash
curl -s http://localhost:8003/health/
```

Expected: `{"status": "ok"}` or HTTP 200.

---

## Test Users Setup

In Keycloak Admin Console (`http://localhost:8080`, admin/admin), verify or create these users:

| User | Password | Roles in `d3-client` | Keycloak Groups |
|---|---|---|---|
| `d3_all_user` | `Test1234!` | `can-login` | `d3:normas`, `d3:documentos`, `d3:leyes` |
| `d3_normas_user` | `Test1234!` | `can-login` | `d3:normas` |
| `d3_no_group_user` | `Test1234!` | `can-login` | (none) |
| `d3_no_access_user` | `Test1234!` | (none) | (none) |

---

## Scenario 1 — Login con `can-login` (Acceso concedido)

**Validates**: FR-001, FR-002, US1-AC1, US1-AC2, SC-001

**Steps**:

1. Abrir `http://localhost:8003/` en el navegador (sin sesión activa)
2. D3 redirige a Keycloak → aparece pantalla de login (usuario + contraseña en el mismo formulario)
3. Introducir `d3_all_user` / `Test1234!`
4. Keycloak verifica `can-login` en `d3-client` → acceso concedido → redirige a D3
5. D3 muestra la página de inicio con la sesión activa

**Expected**: Usuario autenticado en D3, se ve el nombre de usuario o email en la página de inicio. No se pide nombre ni apellido.

---

## Scenario 2 — Login sin `can-login` (Acceso denegado en Keycloak)

**Validates**: FR-002, US1-AC4, SC-001

**Steps**:

1. Abrir `http://localhost:8003/` en navegador en modo incógnito
2. D3 redirige a Keycloak → pantalla de login
3. Introducir `d3_no_access_user` / `Test1234!`
4. Keycloak ejecuta el subflow CONDITIONAL `d3-client-role-check` → `deny-access-authenticator` activa → acceso denegado

**Expected**: Keycloak muestra un mensaje de error (no se redirige de vuelta a D3). D3 no tiene ninguna sesión para este usuario.

---

## Scenario 3 — Acceso a ruta protegida con grupo correcto

**Validates**: FR-003, FR-004, FR-005, US2-AC1, US2-AC2, US2-AC3, SC-002

**Steps** (login con `d3_all_user`):

1. Navegar a `http://localhost:8003/normas/` → se muestra el contenido de normas ✓
2. Navegar a `http://localhost:8003/documentos/` → se muestra el contenido de documentos ✓
3. Navegar a `http://localhost:8003/leyes/` → se muestra el contenido de leyes ✓

**Expected**: Las tres rutas responden HTTP 200 con el contenido correspondiente sin reiniciar sesión (SC-004).

---

## Scenario 4 — Acceso denegado por grupo faltante

**Validates**: FR-006, US2-AC4, US2-AC6, SC-003

**Steps** (login con `d3_normas_user` — solo tiene `d3:normas`):

1. Navegar a `http://localhost:8003/normas/` → se muestra el contenido ✓
2. Navegar a `http://localhost:8003/documentos/` → se muestra página de acceso denegado con el grupo requerido (`d3:documentos`) ✓
3. Navegar a `http://localhost:8003/leyes/` → se muestra página de acceso denegado con el grupo requerido (`d3:leyes`) ✓

**Expected**: HTTP 200 con la página de acceso denegado (no un 403 sin HTML ni un 500). El mensaje indica qué grupo se requiere.

---

## Scenario 5 — Logout explícito

**Validates**: FR-008, US3-AC1, US3-AC2

**Steps** (con sesión activa de `d3_all_user`):

1. Hacer clic en "Cerrar sesión"
2. La sesión D3 termina y el navegador es redirigido (a `/` o a Keycloak logout)
3. Navegar de nuevo a `http://localhost:8003/` → redirige a Keycloak (sin sesión activa)
4. Keycloak muestra el formulario de login (sin pre-relleno de usuario)

**Expected**: La sesión queda completamente invalidada. No hay re-autenticación automática.

---

## Scenario 6 — D1 y D2 no se ven afectados (SC-005)

**Validates**: FR-009, SC-005

**Steps**:

1. Navegar a `http://localhost:8001/` (D1) y autenticarse — funciona igual que antes ✓
2. Navegar a `http://localhost:8002/` (D2) y autenticarse (flujo magic link / password) — funciona igual ✓
3. Verificar que los logs de D1 y D2 no muestran errores relacionados con D3

**Expected**: D1 y D2 funcionan sin ningún cambio observable.

---

## Verificación rápida via logs

```bash
# D3 logs en tiempo real
docker compose logs -f d3

# Verificar que D3 corrió migraciones exitosamente
docker compose logs d3 | grep -E "No migrations|Applying"

# Verificar que Keycloak importó el realm con d3-client
docker compose logs keycloak | grep -i "d3-client"
```

---

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `502 Bad Gateway` en puerto 8003 | Contenedor D3 no inició | `docker compose logs d3` para ver el error |
| `HTTPError: unauthorized_client` | `D3_OIDC_CLIENT_SECRET` no coincide con realm-export.json | Verificar que el secret en `.env` es el mismo que en el JSON |
| `groups` no sincronizados | Client scope `groups` no asignado a `d3-client` en Keycloak | Asignar scope `groups` en la consola o en realm-export.json |
| Keycloak no deniega sin `can-login` | Subflow CONDITIONAL mal configurado | Verificar `negate: true` en `d3-client-role-cfg` authenticatorConfig |
| D3 no tiene base de datos | `init.sql` no creó `d3_db` | `docker compose down --volumes && docker compose up -d` para reinicializar |
