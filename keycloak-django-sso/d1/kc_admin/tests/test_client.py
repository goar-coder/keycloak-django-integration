import pytest
from unittest.mock import MagicMock, patch

from kc_admin.client import (
    KeycloakAdminClient,
    DuplicateUser,
    GroupNotFound,
    KeycloakConnectionError,
    RoleNotFound,
    UserNotFound,
)


@pytest.fixture
def mock_kc_admin():
    with patch('kc_admin.client.KeycloakAdmin') as MockKC:
        instance = MockKC.return_value
        yield instance


@pytest.fixture
def client(mock_kc_admin, settings):
    settings.KEYCLOAK_SERVER_URL = 'http://keycloak:8080'
    settings.KEYCLOAK_REALM = 'app-realm'
    settings.D1_KC_SERVICE_ACCOUNT_CLIENT_ID = 'd1-client'
    settings.D1_KC_SERVICE_ACCOUNT_CLIENT_SECRET = 'secret'
    return KeycloakAdminClient()


def test_list_users_returns_list(client, mock_kc_admin):
    mock_kc_admin.get_users.return_value = [{'id': 'u1', 'email': 'a@b.com'}]
    result = client.list_users()
    assert isinstance(result, list)
    assert result[0]['id'] == 'u1'


def test_create_user_returns_id(client, mock_kc_admin):
    mock_kc_admin.create_user.return_value = 'new-uuid'
    result = client.create_user('a@b.com', 'alice', 'Alice', 'Smith')
    assert result == 'new-uuid'


def test_create_user_raises_duplicate_on_409(client, mock_kc_admin):
    from keycloak.exceptions import KeycloakPostError
    err = KeycloakPostError(response_code=409)
    mock_kc_admin.create_user.side_effect = err
    with pytest.raises(DuplicateUser):
        client.create_user('dup@b.com', 'dup', '', '')


def test_assign_realm_role_calls_correct_methods(client, mock_kc_admin):
    mock_kc_admin.get_realm_role.return_value = {'id': 'role-id', 'name': 'admin'}
    client.assign_realm_role('user-uuid', 'admin')
    mock_kc_admin.assign_realm_roles.assert_called_once_with('user-uuid', [{'id': 'role-id', 'name': 'admin'}])


def test_assign_realm_role_raises_role_not_found(client, mock_kc_admin):
    from keycloak.exceptions import KeycloakGetError
    mock_kc_admin.get_realm_role.side_effect = KeycloakGetError(response_code=404)
    with pytest.raises(RoleNotFound):
        client.assign_realm_role('user-uuid', 'nonexistent')


def test_deactivate_user_calls_update_user(client, mock_kc_admin):
    client.deactivate_user('user-uuid')
    mock_kc_admin.update_user.assert_called_once_with('user-uuid', {'enabled': False})


def test_deactivate_user_raises_user_not_found(client, mock_kc_admin):
    from keycloak.exceptions import KeycloakPutError
    mock_kc_admin.update_user.side_effect = KeycloakPutError(response_code=404)
    with pytest.raises(UserNotFound):
        client.deactivate_user('ghost-uuid')


# --- provision_user ---

def test_provision_user_returns_id(client, mock_kc_admin):
    mock_kc_admin.create_user.return_value = 'prov-uuid'
    result = client.provision_user('new@ex.com', 'newuser', 'New', 'User')
    assert result == 'prov-uuid'
    call_payload = mock_kc_admin.create_user.call_args[0][0]
    assert call_payload['emailVerified'] is False
    assert call_payload['requiredActions'] == ['UPDATE_PASSWORD', 'UPDATE_PROFILE']
    assert 'credentials' not in call_payload or call_payload.get('credentials') == []


def test_provision_user_raises_duplicate_on_409(client, mock_kc_admin):
    from keycloak.exceptions import KeycloakPostError
    mock_kc_admin.create_user.side_effect = KeycloakPostError(response_code=409)
    with pytest.raises(DuplicateUser):
        client.provision_user('dup@ex.com', 'dup')


def test_provision_user_raises_connection_error(client, mock_kc_admin):
    mock_kc_admin.create_user.side_effect = Exception('timeout')
    with pytest.raises(KeycloakConnectionError):
        client.provision_user('err@ex.com', 'erruser')


# --- send_activation_email ---

def test_send_activation_email_calls_send_update_account(client, mock_kc_admin):
    client.send_activation_email('user-uuid')
    mock_kc_admin.send_update_account.assert_called_once_with(
        user_id='user-uuid',
        payload=['UPDATE_PASSWORD', 'UPDATE_PROFILE'],
    )


def test_send_activation_email_raises_connection_error(client, mock_kc_admin):
    mock_kc_admin.send_update_account.side_effect = Exception('smtp down')
    with pytest.raises(KeycloakConnectionError):
        client.send_activation_email('user-uuid')
