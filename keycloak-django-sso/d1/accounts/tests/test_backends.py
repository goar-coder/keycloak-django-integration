import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from accounts.backends import KeycloakOIDCBackend
from accounts.models import UserProfile

User = get_user_model()


@pytest.fixture
def backend():
    return KeycloakOIDCBackend()


@pytest.fixture
def claims():
    return {
        'sub': 'kc-uuid-001',
        'email': 'alice@example.com',
        'realm_access': {'roles': ['admin', 'viewer', 'uma_authorization', 'offline_access']},
        'groups': ['team-a'],
    }


def test_create_user_creates_django_user(db, backend, claims):
    with patch.object(backend, 'get_userinfo', return_value=claims):
        user = backend.create_user(claims)
    profile = UserProfile.objects.get(user=user)
    assert profile.sub == 'kc-uuid-001'


def test_create_user_creates_userprofile(db, backend, claims):
    with patch.object(backend, 'get_userinfo', return_value=claims):
        user = backend.create_user(claims)
    profile = UserProfile.objects.get(user=user)
    assert profile.sub == 'kc-uuid-001'
    assert profile.email == 'alice@example.com'


def test_create_user_sets_unusable_password(db, backend, claims):
    with patch.object(backend, 'get_userinfo', return_value=claims):
        user = backend.create_user(claims)
    assert not user.has_usable_password()


def test_update_user_syncs_roles_excluding_system_roles(db, backend, claims):
    user = User.objects.create_user(username='kc-uuid-001')
    UserProfile.objects.create(user=user, sub='kc-uuid-001')
    backend.update_user(user, claims)
    profile = UserProfile.objects.get(user=user)
    assert 'admin' in profile.roles
    assert 'viewer' in profile.roles
    assert 'uma_authorization' not in profile.roles
    assert 'offline_access' not in profile.roles


def test_update_user_syncs_groups(db, backend, claims):
    user = User.objects.create_user(username='kc-uuid-001')
    UserProfile.objects.create(user=user, sub='kc-uuid-001')
    backend.update_user(user, claims)
    profile = UserProfile.objects.get(user=user)
    assert 'team-a' in profile.groups


def test_update_user_overwrites_not_appends(db, backend, claims):
    user = User.objects.create_user(username='kc-uuid-001')
    UserProfile.objects.create(user=user, sub='kc-uuid-001', roles=['old-role'], groups=['old-group'])
    backend.update_user(user, claims)
    profile = UserProfile.objects.get(user=user)
    assert 'old-role' not in profile.roles
    assert 'old-group' not in profile.groups


# --- Group sync tests (T035) ---

def test_update_user_syncs_d1_group_to_auth_group(db, backend):
    user = User.objects.create_user(username='kc-uuid-002')
    UserProfile.objects.create(user=user, sub='kc-uuid-002')
    claims_with_d1 = {
        'sub': 'kc-uuid-002',
        'email': 'bob@example.com',
        'realm_access': {'roles': ['viewer']},
        'groups': ['d1:worker'],
    }
    backend.update_user(user, claims_with_d1)
    group_names = list(user.groups.values_list('name', flat=True))
    assert 'd1:worker' in group_names


def test_update_user_does_not_sync_d2_groups_to_d1(db, backend):
    user = User.objects.create_user(username='kc-uuid-003')
    UserProfile.objects.create(user=user, sub='kc-uuid-003')
    claims_cross = {
        'sub': 'kc-uuid-003',
        'email': 'cross@example.com',
        'realm_access': {'roles': []},
        'groups': ['d2:viewer', 'd1:rrhh'],
    }
    backend.update_user(user, claims_cross)
    group_names = list(user.groups.values_list('name', flat=True))
    assert 'd2:viewer' not in group_names
    assert 'd1:rrhh' in group_names


def test_update_user_clears_d1_groups_when_removed(db, backend):
    from django.contrib.auth.models import Group
    user = User.objects.create_user(username='kc-uuid-004')
    UserProfile.objects.create(user=user, sub='kc-uuid-004')
    g, _ = Group.objects.get_or_create(name='d1:worker')
    user.groups.add(g)
    claims_empty = {
        'sub': 'kc-uuid-004',
        'email': 'empty@example.com',
        'realm_access': {'roles': []},
        'groups': [],
    }
    backend.update_user(user, claims_empty)
    assert not user.groups.filter(name='d1:worker').exists()


def test_create_user_also_syncs_groups(db, backend):
    claims_with_group = {
        'sub': 'kc-uuid-005',
        'email': 'new@example.com',
        'realm_access': {'roles': []},
        'groups': ['d1:admin'],
    }
    with patch.object(backend, 'get_userinfo', return_value=claims_with_group):
        user = backend.create_user(claims_with_group)
    assert user.groups.filter(name='d1:admin').exists()
