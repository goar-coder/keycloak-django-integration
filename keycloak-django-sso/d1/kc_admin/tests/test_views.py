import json
import pytest
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import Client

from kc_admin.client import (
    DuplicateUser,
    GroupNotFound,
    KeycloakConnectionError,
    RoleNotFound,
    UserNotFound,
)

User = get_user_model()

TARGET_SUB = 'target-kc-uuid'


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='admin-sub')
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def mock_client():
    with patch('kc_admin.views.kc_client') as m:
        yield m


# --- GET /api/users/ ---

def test_list_users_authenticated(auth_client, mock_client):
    mock_client.list_users.return_value = [{'id': 'u1', 'email': 'a@b.com', 'enabled': True, 'roles': [], 'groups': []}]
    resp = auth_client.get('/api/users/')
    assert resp.status_code == 200
    data = json.loads(resp.content)
    assert 'users' in data
    assert data['users'][0]['id'] == 'u1'


def test_list_users_unauthenticated(db):
    resp = Client().get('/api/users/')
    assert resp.status_code == 401


def test_list_users_keycloak_error(auth_client, mock_client):
    mock_client.list_users.side_effect = KeycloakConnectionError('down')
    resp = auth_client.get('/api/users/')
    assert resp.status_code == 502


# --- POST /api/users/create/ ---

def test_create_user_success(auth_client, mock_client):
    mock_client.create_user.return_value = 'new-uuid'
    resp = auth_client.post(
        '/api/users/create/',
        data=json.dumps({'email': 'new@ex.com', 'username': 'newuser', 'password': 'secret123'}),
        content_type='application/json',
    )
    assert resp.status_code == 201
    data = json.loads(resp.content)
    assert data['id'] == 'new-uuid'


def test_create_user_missing_email(auth_client, mock_client):
    resp = auth_client.post(
        '/api/users/create/',
        data=json.dumps({'username': 'noemail', 'password': 'secret123'}),
        content_type='application/json',
    )
    assert resp.status_code == 400


def test_create_user_missing_password(auth_client, mock_client):
    resp = auth_client.post(
        '/api/users/create/',
        data=json.dumps({'email': 'new@ex.com', 'username': 'newuser'}),
        content_type='application/json',
    )
    assert resp.status_code == 400


def test_create_user_duplicate(auth_client, mock_client):
    mock_client.create_user.side_effect = DuplicateUser()
    resp = auth_client.post(
        '/api/users/create/',
        data=json.dumps({'email': 'dup@ex.com', 'username': 'dup', 'password': 'secret123'}),
        content_type='application/json',
    )
    assert resp.status_code == 409


def test_create_user_unauthenticated(db):
    resp = Client().post('/api/users/create/', data='{}', content_type='application/json')
    assert resp.status_code == 401


# --- POST /api/users/<sub>/roles/assign/ ---

def test_assign_role_success(auth_client, mock_client):
    resp = auth_client.post(
        f'/api/users/{TARGET_SUB}/roles/assign/',
        data=json.dumps({'role_name': 'admin'}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    assert json.loads(resp.content)['success'] is True


def test_assign_role_missing_role_name(auth_client, mock_client):
    resp = auth_client.post(
        f'/api/users/{TARGET_SUB}/roles/assign/',
        data=json.dumps({}),
        content_type='application/json',
    )
    assert resp.status_code == 400


def test_assign_role_not_found(auth_client, mock_client):
    mock_client.assign_realm_role.side_effect = RoleNotFound()
    resp = auth_client.post(
        f'/api/users/{TARGET_SUB}/roles/assign/',
        data=json.dumps({'role_name': 'ghost'}),
        content_type='application/json',
    )
    assert resp.status_code == 404


# --- POST /api/users/<sub>/groups/assign/ ---

def test_assign_group_success(auth_client, mock_client):
    resp = auth_client.post(
        f'/api/users/{TARGET_SUB}/groups/assign/',
        data=json.dumps({'group_name': 'team-a'}),
        content_type='application/json',
    )
    assert resp.status_code == 200


def test_assign_group_not_found(auth_client, mock_client):
    mock_client.assign_group.side_effect = GroupNotFound()
    resp = auth_client.post(
        f'/api/users/{TARGET_SUB}/groups/assign/',
        data=json.dumps({'group_name': 'ghost'}),
        content_type='application/json',
    )
    assert resp.status_code == 404


# --- POST /api/users/<sub>/deactivate/ ---

def test_deactivate_success(auth_client, mock_client):
    resp = auth_client.post(f'/api/users/{TARGET_SUB}/deactivate/')
    assert resp.status_code == 200
    data = json.loads(resp.content)
    assert data['enabled'] is False


def test_deactivate_not_found(auth_client, mock_client):
    mock_client.deactivate_user.side_effect = UserNotFound()
    resp = auth_client.post(f'/api/users/{TARGET_SUB}/deactivate/')
    assert resp.status_code == 404


def test_deactivate_self(db):
    user = User.objects.create_user(username=TARGET_SUB)
    c = Client()
    c.force_login(user)
    resp = c.post(f'/api/users/{TARGET_SUB}/deactivate/')
    assert resp.status_code == 409
