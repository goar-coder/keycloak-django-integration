#!/usr/bin/env python3
"""
Crea usuarios en Keycloak con contraseña, grupos y roles de cliente.
Si el usuario ya existe lo actualiza (grupos y roles). Los grupos se
crean automáticamente si no existen.

Uso desde dentro del contenedor d1:
    python3 scripts/create_users.py

Uso desde fuera (apuntando a localhost):
    KEYCLOAK_SERVER_URL=http://localhost:8080 python3 scripts/create_users.py
"""

import os
import sys

try:
    import requests
except ImportError:
    print("ERROR: 'requests' no instalado. Ejecuta: pip install requests")
    sys.exit(1)

# ── Configuración ──────────────────────────────────────────────────────────────
KEYCLOAK_URL   = os.environ.get("KEYCLOAK_SERVER_URL",     "http://keycloak:8080")
REALM          = os.environ.get("KEYCLOAK_REALM",          "app-realm")
ADMIN_USER     = os.environ.get("KEYCLOAK_ADMIN",          "admin")
ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin123")

# ── Usuarios a crear ───────────────────────────────────────────────────────────
# client_roles: { "nombre-cliente": ["rol1", "rol2", ...] }
USERS = [
    {
        "username":     "testadmin",
        "password":     "testadmin123",
        "groups":       ["d1:admin", "d2:admin", "d3:admin"],
        "client_roles": {
            "d1-client": ["can-login"],
            "d2-client": ["auth_loginform", "can-login"],
            "d3-client": ["can-login"],
        },
    },
    {
        "username":     "testuser_data",
        "password":     "testuser_data123",
        "groups":       ["d1:data", "d2:data"],
        "client_roles": {
            "d1-client": ["can-login"],
            "d2-client": ["auth_loginform", "can-login"],
        },
    },
    {
        "username":     "testuser_rrhh_leyes",
        "password":     "testuser_rrhh_leyes123",
        "groups":       ["d1:rrhh", "d3:leyes"],
        "client_roles": {
            "d1-client": ["can-login"],
            "d3-client": ["can-login"],
        },
    },
    {
        "username":     "user_admin_data",
        "password":     "user_admin_data123",
        "groups":       ["d1:data", "d2:data"],
        "client_roles": {
            "d1-client": ["can-login"],
            "d2-client": ["auth_loginform", "can-login"],
        },
    },
    {
        "username":     "d1_user_rrhh",
        "password":     "d1_user_rrhh123",
        "groups":       ["d1:rrhh"],
        "client_roles": {"d1-client": ["can-login"]},
    },
    {
        "username":     "d1_user_worker",
        "password":     "d1_user_worker123",
        "groups":       ["d1:worker"],
        "client_roles": {"d1-client": ["can-login"]},
    },
    {
        "username":     "d1_user_data",
        "password":     "d1_user_data123",
        "groups":       ["d1:data"],
        "client_roles": {"d1-client": ["can-login"]},
    },
    {
        "username":     "d1_user_admin",
        "password":     "d1_user_admin123",
        "groups":       ["d1:admin"],
        "client_roles": {"d1-client": ["can-login"]},
    },
    {
        "username":     "d2_user_report",
        "password":     "d2_user_report123",
        "groups":       ["d2:report"],
        "client_roles": {"d2-client": ["auth_loginform", "can-login"]},
    },
    {
        "username":     "d2_user_data",
        "password":     "d2_user_data123",
        "groups":       ["d2:data"],
        "client_roles": {"d2-client": ["auth_loginform", "can-login"]},
    },
    {
        "username":     "d2_user_editor",
        "password":     "d2_user_editor123",
        "groups":       ["d2:editor"],
        "client_roles": {"d2-client": ["auth_loginform", "can-login"]},
    },
    {
        "username":     "d2_user_admin",
        "password":     "d2_user_admin123",
        "groups":       ["d2:admin"],
        "client_roles": {"d2-client": ["can-login"]},
    },
    {
        "username":     "d2_transcriptor",
        "password":     "d2_transcriptor123",
        "groups":       ["d2:editor"],
        "client_roles": {"d2-client": ["auth_autologin", "can-login"]},
    },
    {
        "username":     "d3_user_normas",
        "password":     "d3_user_normas123",
        "groups":       ["d3:normas"],
        "client_roles": {"d3-client": ["can-login"]},
    },
    {
        "username":     "d3_user_documentos",
        "password":     "d3_user_documentos123",
        "groups":       ["d3:documentos"],
        "client_roles": {"d3-client": ["can-login"]},
    },
    {
        "username":     "d3_user_leyes",
        "password":     "d3_user_leyes123",
        "groups":       ["d3:leyes"],
        "client_roles": {"d3-client": ["can-login"]},
    },
    {
        "username":     "d3_user_admin",
        "password":     "d3_user_admin123",
        "groups":       ["d3:admin"],
        "client_roles": {"d3-client": ["can-login"]},
    },
]

# ── Cache de clientes y roles ──────────────────────────────────────────────────
# { "d1-client": {"id": "...", "roles": {"can-login": {"id":"..","name":".."}}} }
_client_cache: dict = {}


def _load_client(session, client_id_str):
    """Carga y cachea el UUID del cliente y sus roles disponibles."""
    if client_id_str in _client_cache:
        return _client_cache[client_id_str]

    base = f"{KEYCLOAK_URL}/admin/realms/{REALM}"

    resp = session.get(f"{base}/clients", params={"clientId": client_id_str})
    resp.raise_for_status()
    clients = resp.json()
    if not clients:
        print(f"  [WARN] cliente '{client_id_str}' no encontrado en el realm")
        return None

    client_uuid = clients[0]["id"]

    resp = session.get(f"{base}/clients/{client_uuid}/roles")
    resp.raise_for_status()
    roles = {r["name"]: {"id": r["id"], "name": r["name"]} for r in resp.json()}

    _client_cache[client_id_str] = {"id": client_uuid, "roles": roles}
    return _client_cache[client_id_str]


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_admin_token():
    url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
    resp = requests.post(url, data={
        "grant_type": "password",
        "client_id":  "admin-cli",
        "username":   ADMIN_USER,
        "password":   ADMIN_PASSWORD,
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_or_create_group(session, group_name):
    """Devuelve el ID del grupo, creándolo si no existe."""
    base = f"{KEYCLOAK_URL}/admin/realms/{REALM}"

    resp = session.get(f"{base}/groups", params={"search": group_name, "exact": "true"})
    resp.raise_for_status()
    for g in resp.json():
        if g["name"] == group_name:
            return g["id"]

    resp = session.post(f"{base}/groups", json={"name": group_name})
    if resp.status_code == 201:
        group_id = resp.headers["Location"].rstrip("/").split("/")[-1]
        print(f"    [grupo creado] {group_name}")
        return group_id

    print(f"    [ERROR] no se pudo crear el grupo '{group_name}': {resp.status_code} {resp.text}")
    return None


def assign_groups(session, user_id, groups):
    base = f"{KEYCLOAK_URL}/admin/realms/{REALM}"
    for group_name in groups:
        group_id = get_or_create_group(session, group_name)
        if group_id is None:
            continue
        resp = session.put(f"{base}/users/{user_id}/groups/{group_id}")
        if resp.status_code == 204:
            print(f"    → grupo '{group_name}' asignado")
        else:
            print(f"    [ERROR] grupo '{group_name}': {resp.status_code} {resp.text}")


def assign_client_roles(session, user_id, client_roles):
    """Asigna roles de cliente al usuario."""
    base = f"{KEYCLOAK_URL}/admin/realms/{REALM}"
    for client_id_str, role_names in client_roles.items():
        client = _load_client(session, client_id_str)
        if client is None:
            continue

        client_uuid = client["id"]
        available_roles = client["roles"]

        roles_to_assign = []
        for role_name in role_names:
            if role_name in available_roles:
                roles_to_assign.append(available_roles[role_name])
            else:
                print(f"    [WARN] rol '{role_name}' no existe en '{client_id_str}' — ignorado")

        if not roles_to_assign:
            continue

        resp = session.post(
            f"{base}/users/{user_id}/role-mappings/clients/{client_uuid}",
            json=roles_to_assign,
        )
        if resp.status_code == 204:
            names = ", ".join(r["name"] for r in roles_to_assign)
            print(f"    → roles [{names}] en '{client_id_str}' asignados")
        else:
            print(f"    [ERROR] roles en '{client_id_str}': {resp.status_code} {resp.text}")


def process_user(session, username, password, groups, client_roles):
    base = f"{KEYCLOAK_URL}/admin/realms/{REALM}"

    # ¿Existe ya?
    resp = session.get(f"{base}/users", params={"username": username, "exact": "true"})
    resp.raise_for_status()
    existing = resp.json()

    if existing:
        user_id = existing[0]["id"]
        print(f"  [ya existe] {username}  →  actualizando grupos y roles")
    else:
        # Crear usuario
        resp = session.post(f"{base}/users", json={
            "username":      username,
            "firstName":     username,
            "lastName":      username,
            "email":         f"{username}@home.es",
            "enabled":       True,
            "emailVerified": True,
        })
        if resp.status_code != 201:
            print(f"  [ERROR] no se pudo crear '{username}': {resp.status_code} {resp.text}")
            return

        user_id = resp.headers["Location"].rstrip("/").split("/")[-1]

        # Establecer contraseña
        resp = session.put(
            f"{base}/users/{user_id}/reset-password",
            json={"type": "password", "value": password, "temporary": False},
        )
        if resp.status_code != 204:
            print(f"  [ERROR] contraseña para '{username}': {resp.status_code} {resp.text}")
            return

        print(f"  [creado] {username}")

    assign_groups(session, user_id, groups)
    assign_client_roles(session, user_id, client_roles)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"Keycloak: {KEYCLOAK_URL}  |  realm: {REALM}\n")

    try:
        token = get_admin_token()
    except Exception as e:
        print(f"[FATAL] no se pudo obtener token de admin: {e}")
        sys.exit(1)

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    })

    for user in USERS:
        print(f"► {user['username']}")
        try:
            process_user(
                session,
                user["username"],
                user["password"],
                user.get("groups", []),
                user.get("client_roles", {}),
            )
        except Exception as e:
            print(f"  [ERROR inesperado] {e}  →  continuando con el siguiente")
        print()

    print("Proceso completado.")


if __name__ == "__main__":
    main()
