import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from accounts.backends import D3KeycloakOIDCBackend
from accounts.models import UserProfile

User = get_user_model()


@pytest.fixture
def backend():
    return D3KeycloakOIDCBackend()


@pytest.fixture
def claims():
    return {
        'sub': 'kc-d3-uuid-001',
        'email': 'alice@example.com',
        'realm_access': {'roles': ['viewer', 'uma_authorization', 'offline_access']},
        'groups': ['d3:normas', 'd1:admin', 'other:group'],
    }


def test_create_user_creates_userprofile(db, backend, claims):
    with patch.object(backend, 'get_userinfo', return_value=claims):
        user = backend.create_user(claims)
    profile = UserProfile.objects.get(user=user)
    assert profile.sub == 'kc-d3-uuid-001'
    assert profile.email == 'alice@example.com'


def test_create_user_sets_unusable_password(db, backend, claims):
    with patch.object(backend, 'get_userinfo', return_value=claims):
        user = backend.create_user(claims)
    assert not user.has_usable_password()


def test_update_user_syncs_only_d3_groups(db, backend, claims):
    user = User.objects.create_user(username='kc-d3-uuid-001')
    UserProfile.objects.create(user=user, sub='kc-d3-uuid-001')
    backend.update_user(user, claims)
    group_names = list(user.groups.values_list('name', flat=True))
    assert 'd3:normas' in group_names
    assert 'd1:admin' not in group_names
    assert 'other:group' not in group_names


def test_update_user_excludes_system_roles(db, backend, claims):
    user = User.objects.create_user(username='kc-d3-uuid-002')
    UserProfile.objects.create(user=user, sub='kc-d3-uuid-002')
    backend.update_user(user, claims)
    profile = UserProfile.objects.get(user=user)
    assert 'uma_authorization' not in profile.roles
    assert 'offline_access' not in profile.roles
    assert 'viewer' in profile.roles


def test_update_user_clears_d3_groups_when_removed(db, backend):
    user = User.objects.create_user(username='kc-d3-uuid-003')
    UserProfile.objects.create(user=user, sub='kc-d3-uuid-003')
    g, _ = Group.objects.get_or_create(name='d3:normas')
    user.groups.add(g)
    backend.update_user(user, {'sub': 'kc-d3-uuid-003', 'email': '', 'realm_access': {'roles': []}, 'groups': []})
    assert not user.groups.filter(name='d3:normas').exists()


def test_update_user_strips_group_path_prefix(db, backend):
    user = User.objects.create_user(username='kc-d3-uuid-004')
    UserProfile.objects.create(user=user, sub='kc-d3-uuid-004')
    claims_with_path = {
        'sub': 'kc-d3-uuid-004',
        'email': 'path@example.com',
        'realm_access': {'roles': []},
        'groups': ['/d3:documentos'],
    }
    backend.update_user(user, claims_with_path)
    assert user.groups.filter(name='d3:documentos').exists()
