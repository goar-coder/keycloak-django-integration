# Feature Specification: D3 Django Service

**Feature Branch**: `005-d3-django-service`

**Created**: 2026-06-26

**Status**: Draft

**Input**: Nuevo servicio Django D3, similar a D1, con autenticación Keycloak, control de acceso por rol `can-login` en `d3-client`, y tres rutas protegidas por grupo: normas, documentos, leyes.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Autenticación y control de acceso por rol (Priority: P1)

Un usuario que tiene el rol `can-login` en `d3-client` accede a D3 sin sesión activa. Es redirigido a Keycloak, introduce sus credenciales (usuario y contraseña), y al autenticarse correctamente queda con una sesión activa en D3. Un usuario sin ese rol es rechazado directamente en Keycloak y no obtiene ninguna sesión en D3.

**Why this priority**: Es el prerequisito de todo lo demás. Sin la puerta de acceso por rol, las rutas protegidas por grupo no tienen sentido. Valida que el nuevo cliente `d3-client` está correctamente configurado en Keycloak y que el flujo OIDC funciona de extremo a extremo.

**Independent Test**: Crear un usuario con `can-login` en `d3-client` y navegar a D3 sin sesión. Verificar que se redirige a Keycloak, que tras autenticarse se regresa a D3 con sesión activa. Crear un segundo usuario sin ningún rol en `d3-client` y verificar que Keycloak lo rechaza sin que D3 le conceda sesión.

**Acceptance Scenarios**:

1. **Given** un usuario con rol `can-login` en `d3-client` y sin sesión activa en D3, **When** navega a cualquier ruta protegida de D3, **Then** es redirigido a Keycloak y ve la pantalla de login.
2. **Given** el usuario introduce sus credenciales correctas en Keycloak, **When** Keycloak valida la autenticación y verifica el rol `can-login`, **Then** el usuario es redirigido a D3 con una sesión activa.
3. **Given** el usuario introduce credenciales incorrectas, **When** Keycloak rechaza la autenticación, **Then** el usuario ve un error en Keycloak y no obtiene sesión en D3.
4. **Given** un usuario sin el rol `can-login` en `d3-client`, **When** intenta autenticarse en Keycloak para acceder a D3, **Then** Keycloak deniega el acceso antes de redirigir a D3 y el usuario ve un mensaje de error.

---

### User Story 2 - Acceso a rutas protegidas por grupo (Priority: P2)

Un usuario autenticado en D3 (con `can-login`) puede acceder únicamente a las rutas para las que su cuenta tiene el grupo correspondiente en Keycloak. Si intenta acceder a una ruta para la que no tiene grupo, ve una página de acceso denegado clara. Las tres rutas independientes son: `/normas/`, `/documentos/` y `/leyes/`, protegidas respectivamente por los grupos `d3:normas`, `d3:documentos` y `d3:leyes`.

**Why this priority**: Es la funcionalidad diferenciadora de D3. El control de acceso por grupo determina qué contenido puede ver cada usuario dentro de la aplicación.

**Independent Test**: Crear tres usuarios, cada uno con `can-login` y solo uno de los tres grupos. Verificar que cada usuario accede únicamente a su ruta correspondiente y recibe "acceso denegado" en las otras dos. Crear un cuarto usuario con los tres grupos y verificar que puede acceder a las tres rutas.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado con membresía en el grupo `d3:normas`, **When** navega a `/normas/`, **Then** ve el contenido de la sección normas.
2. **Given** un usuario autenticado con membresía en el grupo `d3:documentos`, **When** navega a `/documentos/`, **Then** ve el contenido de la sección documentos.
3. **Given** un usuario autenticado con membresía en el grupo `d3:leyes`, **When** navega a `/leyes/`, **Then** ve el contenido de la sección leyes.
4. **Given** un usuario autenticado que NO es miembro del grupo `d3:normas`, **When** navega a `/normas/`, **Then** ve una página de "acceso denegado" clara con indicación de qué grupo requiere esa sección.
5. **Given** un usuario autenticado miembro de los tres grupos, **When** navega sucesivamente a `/normas/`, `/documentos/` y `/leyes/`, **Then** puede acceder a las tres sin reiniciar sesión.
6. **Given** un usuario autenticado con `can-login` pero sin ningún grupo de D3, **When** navega a cualquiera de las tres rutas protegidas, **Then** ve la página de acceso denegado en cada una.

---

### User Story 3 - Cierre de sesión explícito (Priority: P3)

Un usuario autenticado en D3 puede cerrar sesión explícitamente. Al hacerlo, su sesión en D3 termina y Keycloak es notificado para invalidar la sesión SSO, evitando que otras aplicaciones del mismo realm reutilicen la sesión sin re-autenticación.

**Why this priority**: Seguridad básica que cierra el ciclo de autenticación. Necesario antes de considerar el servicio completo, pero no bloquea validar P1 y P2.

**Independent Test**: Autenticarse en D3, usar la opción de logout, verificar que la sesión D3 termina (cualquier ruta protegida redirige a Keycloak), y verificar que la sesión SSO de Keycloak también fue invalidada.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado en D3, **When** hace clic en "Cerrar sesión", **Then** su sesión en D3 termina y el siguiente acceso a una ruta protegida redirige a Keycloak.
2. **Given** el usuario ha cerrado sesión, **When** accede de nuevo a D3, **Then** debe autenticarse desde cero (no reutiliza la sesión previa).

---

### Edge Cases

- ¿Qué pasa si un usuario tiene `can-login` pero ninguno de los tres grupos de D3? Puede autenticarse en D3 y ver la página de inicio, pero ve acceso denegado en las tres rutas protegidas.
- ¿Qué pasa si Keycloak no está disponible cuando el usuario intenta hacer login? D3 muestra un error de servicio no disponible; no se concede acceso.
- ¿Qué pasa si la sesión expira mientras el usuario está navegando en D3? El siguiente request redirige al usuario a Keycloak para re-autenticarse.
- ¿Puede un usuario tener los tres grupos a la vez? Sí, y puede acceder a las tres rutas.
- ¿Los cambios en grupos de Keycloak se reflejan sin re-login? Los grupos se sincronizan en cada login o renovación de sesión. Si el grupo se elimina durante la sesión activa, el acceso se revoca en la próxima comprobación.
- ¿D1, D2 y sus configuraciones de Keycloak se ven afectados? No. D3 usa su propio cliente `d3-client` y sus propios grupos y roles. D1 y D2 no se tocan.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: D3 MUST redirigir a Keycloak a cualquier usuario que intente acceder a una ruta protegida sin sesión activa.
- **FR-002**: Solo los usuarios con el rol `can-login` en `d3-client` MUST obtener sesión en D3 tras autenticarse en Keycloak. Los usuarios sin ese rol MUST ser rechazados en Keycloak antes de llegar a D3.
- **FR-003**: La ruta `/normas/` MUST ser accesible únicamente a usuarios autenticados y miembros del grupo `d3:normas`.
- **FR-004**: La ruta `/documentos/` MUST ser accesible únicamente a usuarios autenticados y miembros del grupo `d3:documentos`.
- **FR-005**: La ruta `/leyes/` MUST ser accesible únicamente a usuarios autenticados y miembros del grupo `d3:leyes`.
- **FR-006**: Los usuarios autenticados que no pertenezcan al grupo requerido MUST ver una página de acceso denegado específica que indique qué grupo requiere la sección a la que intentaron acceder.
- **FR-007**: D3 MUST sincronizar la pertenencia a grupos de Keycloak en cada autenticación, de forma que la asignación de grupos en Keycloak sea la fuente de verdad.
- **FR-008**: D3 MUST proveer una opción de cierre de sesión explícito que invalide la sesión local y notifique a Keycloak (backchannel logout o redirect logout).
- **FR-009**: Los cambios en D3 MUST NO afectar a D1, D2 ni a ninguna configuración existente de Keycloak (realm, clientes d1-client y d2-client, flujos existentes).
- **FR-010**: D3 MUST tener una página de inicio accesible a cualquier usuario autenticado con `can-login`, que muestre las secciones disponibles para ese usuario según sus grupos.

### Key Entities

- **Usuario D3**: Un usuario de Keycloak que tiene el rol `can-login` en `d3-client`. Es la unidad de acceso al servicio. Tiene cero o más grupos de D3 que determinan qué rutas puede visitar.
- **Sesión D3**: Contexto autenticado creado al completar el login con Keycloak. Asociada a un usuario y a sus grupos actuales. Expira según la configuración de sesión del realm.
- **Grupo de ruta**: Una de las tres membresías de Keycloak (`d3:normas`, `d3:documentos`, `d3:leyes`) que habilita el acceso a la ruta correspondiente. La pertenencia se gestiona en Keycloak.
- **Ruta protegida**: Una de las tres secciones de D3 (`/normas/`, `/documentos/`, `/leyes/`). Requiere autenticación más membresía en el grupo correspondiente.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% de los usuarios sin `can-login` en `d3-client` son rechazados antes de obtener cualquier sesión en D3 — cero accesos concedidos a usuarios sin ese rol.
- **SC-002**: 100% de los usuarios con `can-login` y el grupo correcto pueden acceder a su ruta correspondiente sin errores.
- **SC-003**: 100% de los intentos de acceso a una ruta sin el grupo requerido resultan en una página de "acceso denegado" comprensible — cero errores de aplicación (500) mostrados al usuario.
- **SC-004**: Un usuario con los tres grupos puede acceder a las tres rutas en la misma sesión sin re-autenticarse.
- **SC-005**: Cero cambios observables en el comportamiento de D1 y D2 tras desplegar D3.
- **SC-006**: El flujo completo login → acceso a ruta protegida se completa en menos de 10 segundos en condiciones normales de red local.

---

## Assumptions

- D3 reutiliza la misma instancia de Keycloak (`app-realm`) y el mismo servidor PostgreSQL que D1 y D2. Se añade un nuevo cliente `d3-client` al realm y una nueva base de datos `d3_db`.
- El flujo de autenticación de D3 en Keycloak es idéntico al de D1: login con usuario y contraseña en un mismo formulario (sin identity-first), con un subflow CONDITIONAL que deniega acceso si el usuario no tiene `can-login`.
- Los grupos `d3:normas`, `d3:documentos` y `d3:leyes` son grupos nuevos en Keycloak creados para D3. No interfieren con grupos existentes de D1.
- El contenido de las rutas protegidas (`/normas/`, `/documentos/`, `/leyes/`) es informativo/estático en esta versión. No se requiere gestión de contenido dinámico.
- D3 tiene su propio puerto de escucha (p.ej. `8003`) y su propia entrada en `docker-compose.yml`.
- Los grupos de Keycloak se sincronizan a D3 en cada login (igual que D1 sincroniza roles y grupos). D3 no consulta la API de Keycloak en cada request; confía en la sesión Django sincronizada al login.
- No se requiere gestión de usuarios desde D3 (a diferencia de D1, que puede crear usuarios vía Admin API). D3 es solo lectura respecto a Keycloak.
- La sesión de D3 no tiene requisitos de duración especiales más allá de los valores por defecto del realm. Si en el futuro se necesita expiración específica, se tratará como una nueva feature.
