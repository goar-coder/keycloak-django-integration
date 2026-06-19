import pytest
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client

from kc_admin.client import (
    DuplicateUser,
    GroupNotFound,
    KeycloakConnectionError,
    RoleNotFound,
)

User = get_user_model()

PROVISION_URL = '/provision/'

VALID_POST = {
    'username': 'newuser',
    'email': 'newuser@example.com',
    'first_name': 'New',
    'last_name': 'User',
    'groups': ['d1:worker'],
    'role': '',
}


@pytest.fixture
def admin_client(db):
    user = User.objects.create_user(username='admin-user')
    group, _ = Group.objects.get_or_create(name='d1:admin')
    user.groups.add(group)
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def non_admin_client(db):
    user = User.objects.create_user(username='rrhh-user')
    group, _ = Group.objects.get_or_create(name='d1:rrhh')
    user.groups.add(group)
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def mock_kc():
    with patch('dashboard.views.kc_client') as m:
        m.list_groups.return_value = [
            {'name': 'd1:rrhh', 'id': 'g1'},
            {'name': 'd1:worker', 'id': 'g2'},
            {'name': 'd1:admin', 'id': 'g3'},
            {'name': 'd2:viewer', 'id': 'g4'},
            {'name': 'd2:editor', 'id': 'g5'},
            {'name': 'd2:admin', 'id': 'g6'},
        ]
        m.list_assignable_roles.return_value = []
        yield m


# --- GET ---

def test_get_provision_admin(admin_client, mock_kc):
    resp = admin_client.get(PROVISION_URL)
    assert resp.status_code == 200


def test_get_provision_non_admin(non_admin_client, mock_kc):
    resp = non_admin_client.get(PROVISION_URL)
    assert resp.status_code == 302
    assert 'access-denied' in resp['Location']


def test_get_provision_unauthenticated(db):
    resp = Client().get(PROVISION_URL)
    assert resp.status_code == 302
    assert 'oidc' in resp['Location']


# --- POST success ---

def test_post_provision_success(admin_client, mock_kc):
    mock_kc.provision_user.return_value = 'new-uuid'
    mock_kc.assign_group.return_value = None
    mock_kc.send_activation_email.return_value = None

    resp = admin_client.post(PROVISION_URL, data=VALID_POST)
    assert resp.status_code == 200
    assert resp.context['success'] is True
    assert resp.context['email_sent'] is True
    assert resp.context['success_email'] == 'newuser@example.com'
    assert resp.context['warnings'] == []


def test_post_provision_success_no_groups_no_role(admin_client, mock_kc):
    mock_kc.provision_user.return_value = 'new-uuid'
    mock_kc.send_activation_email.return_value = None

    resp = admin_client.post(PROVISION_URL, data={
        'username': 'bare', 'email': 'bare@ex.com', 'first_name': '', 'last_name': '', 'role': '',
    })
    assert resp.status_code == 200
    assert resp.context['success'] is True
    mock_kc.assign_group.assert_not_called()
    mock_kc.assign_realm_role.assert_not_called()


# --- POST duplicate ---

def test_post_duplicate_user(admin_client, mock_kc):
    mock_kc.provision_user.side_effect = DuplicateUser('newuser')

    resp = admin_client.post(PROVISION_URL, data=VALID_POST)
    assert resp.status_code == 200
    assert not resp.context.get('success')
    assert resp.context['form'].non_field_errors()


def test_post_connection_error_on_create(admin_client, mock_kc):
    mock_kc.provision_user.side_effect = KeycloakConnectionError('down')

    resp = admin_client.post(PROVISION_URL, data=VALID_POST)
    assert resp.status_code == 200
    assert not resp.context.get('success')
    assert resp.context['form'].non_field_errors()


# --- POST missing required fields ---

def test_post_missing_username(admin_client, mock_kc):
    resp = admin_client.post(PROVISION_URL, data={'email': 'x@ex.com', 'role': ''})
    assert resp.status_code == 200
    assert not resp.context.get('success')
    assert resp.context['form'].errors


def test_post_missing_email(admin_client, mock_kc):
    resp = admin_client.post(PROVISION_URL, data={'username': 'x', 'role': ''})
    assert resp.status_code == 200
    assert not resp.context.get('success')
    assert resp.context['form'].errors


# --- POST email failure ---

def test_post_email_fails(admin_client, mock_kc):
    mock_kc.provision_user.return_value = 'new-uuid'
    mock_kc.assign_group.return_value = None
    mock_kc.send_activation_email.side_effect = KeycloakConnectionError('smtp down')

    resp = admin_client.post(PROVISION_URL, data=VALID_POST)
    assert resp.status_code == 200
    assert resp.context['success'] is True
    assert resp.context['email_sent'] is False
    assert len(resp.context['warnings']) > 0


# --- POST group assignment failure ---

def test_post_group_assign_fails(admin_client, mock_kc):
    mock_kc.provision_user.return_value = 'new-uuid'
    mock_kc.assign_group.side_effect = KeycloakConnectionError('group error')
    mock_kc.send_activation_email.return_value = None

    resp = admin_client.post(PROVISION_URL, data=VALID_POST)
    assert resp.status_code == 200
    assert resp.context['success'] is True
    assert len(resp.context['warnings']) > 0


# --- POST role assignment failure ---

def test_post_role_assign_fails(admin_client, mock_kc):
    mock_kc.list_assignable_roles.return_value = [{'name': 'ghost-role', 'type': 'realm', 'client': ''}]
    mock_kc.provision_user.return_value = 'new-uuid'
    mock_kc.assign_realm_role.side_effect = RoleNotFound('ghost-role')
    mock_kc.send_activation_email.return_value = None

    resp = admin_client.post(PROVISION_URL, data={**VALID_POST, 'groups': [], 'role': 'realm::ghost-role'})
    assert resp.status_code == 200
    assert resp.context['success'] is True
    assert len(resp.context['warnings']) > 0
