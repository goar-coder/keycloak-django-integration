import logging
import time

from django.conf import settings
from keycloak import KeycloakAdmin
from keycloak.exceptions import (
    KeycloakGetError,
    KeycloakPostError,
    KeycloakPutError,
    KeycloakDeleteError,
    KeycloakConnectionError as _KCConnError,
)

logger = logging.getLogger('kc_admin')


class UserNotFound(Exception):
    pass


class RoleNotFound(Exception):
    pass


class GroupNotFound(Exception):
    pass


class DuplicateUser(Exception):
    pass


class KeycloakConnectionError(Exception):
    pass


class KeycloakAdminClient:

    def __init__(self):
        self._admin = None

    def _get_admin(self):
        if self._admin is None:
            self._admin = KeycloakAdmin(
                server_url=settings.KEYCLOAK_SERVER_URL,
                realm_name=settings.KEYCLOAK_REALM,
                client_id=settings.D1_KC_SERVICE_ACCOUNT_CLIENT_ID,
                client_secret_key=settings.D1_KC_SERVICE_ACCOUNT_CLIENT_SECRET,
                verify=getattr(settings, 'OIDC_VERIFY_SSL', True),
            )
        return self._admin

    def _log(self, action, **kwargs):
        logger.info('action=%s %s', action, ' '.join(f'{k}={v}' for k, v in kwargs.items()))

    def list_users(self):
        start = time.monotonic()
        try:
            users = self._get_admin().get_users({})
            self._log('kc_list_users', count=len(users), duration_ms=int((time.monotonic() - start) * 1000))
            return users
        except (_KCConnError, Exception) as exc:
            logger.error('action=kc_list_users_error error=%s', exc)
            raise KeycloakConnectionError(str(exc)) from exc

    def create_user(self, email: str, username: str, first_name: str = '', last_name: str = '', password: str = '') -> str:
        start = time.monotonic()
        payload = {
            'email': email,
            'username': username,
            'firstName': first_name,
            'lastName': last_name,
            'enabled': True,
            'emailVerified': True,
            'credentials': [{'type': 'password', 'value': password, 'temporary': False}] if password else [],
        }
        try:
            user_id = self._get_admin().create_user(payload)
            self._log('kc_create_user', username=username, id=user_id, duration_ms=int((time.monotonic() - start) * 1000))
            return user_id
        except KeycloakPostError as exc:
            if exc.response_code == 409:
                raise DuplicateUser(username) from exc
            raise KeycloakConnectionError(str(exc)) from exc
        except Exception as exc:
            raise KeycloakConnectionError(str(exc)) from exc

    def list_assignable_roles(self) -> list:
        start = time.monotonic()
        try:
            admin = self._get_admin()
            realm_roles = [
                {'name': r['name'], 'type': 'realm', 'client': ''}
                for r in admin.get_realm_roles()
                if not r['name'].startswith('default-roles') and r['name'] not in ('uma_authorization', 'offline_access')
            ]
            clients = admin.get_clients()
            client_roles = []
            for client_id in ('d1-client', 'd2-client'):
                client = next((c for c in clients if c['clientId'] == client_id), None)
                if client:
                    client_roles += [
                        {'name': r['name'], 'type': 'client', 'client': client_id}
                        for r in admin.get_client_roles(client['id'])
                    ]
            roles = realm_roles + client_roles
            self._log('kc_list_roles', count=len(roles), duration_ms=int((time.monotonic() - start) * 1000))
            return roles
        except Exception as exc:
            logger.error('action=kc_list_roles_error error=%s', exc)
            raise KeycloakConnectionError(str(exc)) from exc

    def assign_realm_role(self, user_id: str, role_name: str) -> None:
        start = time.monotonic()
        try:
            role = self._get_admin().get_realm_role(role_name)
            self._get_admin().assign_realm_roles(user_id, [role])
            self._log('kc_assign_role', user_id=user_id, role=role_name, duration_ms=int((time.monotonic() - start) * 1000))
        except KeycloakGetError as exc:
            if exc.response_code == 404:
                raise RoleNotFound(role_name) from exc
            raise KeycloakConnectionError(str(exc)) from exc
        except KeycloakPostError as exc:
            if exc.response_code == 404:
                raise UserNotFound(user_id) from exc
            raise KeycloakConnectionError(str(exc)) from exc
        except Exception as exc:
            raise KeycloakConnectionError(str(exc)) from exc

    def assign_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        start = time.monotonic()
        try:
            admin = self._get_admin()
            clients = admin.get_clients()
            client = next((c for c in clients if c['clientId'] == client_id), None)
            if not client:
                raise RoleNotFound(f'{client_id}.{role_name}')
            role = admin.get_client_role(client['id'], role_name)
            admin.assign_client_role(user_id, client['id'], [role])
            self._log('kc_assign_client_role', user_id=user_id, client=client_id, role=role_name, duration_ms=int((time.monotonic() - start) * 1000))
        except RoleNotFound:
            raise
        except KeycloakGetError as exc:
            if exc.response_code == 404:
                raise RoleNotFound(role_name) from exc
            raise KeycloakConnectionError(str(exc)) from exc
        except Exception as exc:
            raise KeycloakConnectionError(str(exc)) from exc

    def list_groups(self) -> list:
        start = time.monotonic()
        try:
            groups = self._get_admin().get_groups()
            result = [{'name': g['name'], 'id': g['id']} for g in groups]
            self._log('kc_list_groups', count=len(result), duration_ms=int((time.monotonic() - start) * 1000))
            return sorted(result, key=lambda g: g['name'])
        except Exception as exc:
            logger.error('action=kc_list_groups_error error=%s', exc)
            raise KeycloakConnectionError(str(exc)) from exc

    def assign_group(self, user_id: str, group_name: str) -> None:
        start = time.monotonic()
        try:
            groups = self._get_admin().get_groups({'search': group_name})
            matched = [g for g in groups if g['name'] == group_name]
            if not matched:
                raise GroupNotFound(group_name)
            self._get_admin().group_user_add(user_id, matched[0]['id'])
            self._log('kc_assign_group', user_id=user_id, group=group_name, duration_ms=int((time.monotonic() - start) * 1000))
        except GroupNotFound:
            raise
        except KeycloakGetError as exc:
            if exc.response_code == 404:
                raise UserNotFound(user_id) from exc
            raise KeycloakConnectionError(str(exc)) from exc
        except Exception as exc:
            raise KeycloakConnectionError(str(exc)) from exc

    def provision_user(self, email: str, username: str, first_name: str = '', last_name: str = '') -> str:
        start = time.monotonic()
        payload = {
            'email': email,
            'username': username,
            'firstName': first_name,
            'lastName': last_name,
            'enabled': True,
            'emailVerified': False,
            'requiredActions': ['UPDATE_PASSWORD', 'UPDATE_PROFILE'],
        }
        try:
            user_id = self._get_admin().create_user(payload)
            self._log('kc_provision_user', username=username, id=user_id, duration_ms=int((time.monotonic() - start) * 1000))
            return user_id
        except KeycloakPostError as exc:
            if exc.response_code == 409:
                raise DuplicateUser(username) from exc
            raise KeycloakConnectionError(str(exc)) from exc
        except Exception as exc:
            raise KeycloakConnectionError(str(exc)) from exc

    def send_activation_email(self, user_id: str) -> None:
        start = time.monotonic()
        try:
            self._get_admin().send_update_account(
                user_id=user_id,
                payload=['UPDATE_PASSWORD', 'UPDATE_PROFILE'],
            )
            self._log('kc_send_activation_email', user_id=user_id, duration_ms=int((time.monotonic() - start) * 1000))
        except Exception as exc:
            logger.error('action=kc_send_activation_email_error user_id=%s error=%s', user_id, exc)
            raise KeycloakConnectionError(str(exc)) from exc

    def deactivate_user(self, user_id: str) -> None:
        start = time.monotonic()
        try:
            self._get_admin().update_user(user_id, {'enabled': False})
            self._log('kc_deactivate_user', user_id=user_id, duration_ms=int((time.monotonic() - start) * 1000))
        except KeycloakPutError as exc:
            if exc.response_code == 404:
                raise UserNotFound(user_id) from exc
            raise KeycloakConnectionError(str(exc)) from exc
        except Exception as exc:
            raise KeycloakConnectionError(str(exc)) from exc
