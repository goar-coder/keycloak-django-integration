import pytest
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model

from accounts.backends import D2OIDCBackend

User = get_user_model()


@pytest.fixture
def backend():
    return D2OIDCBackend()


def test_sync_d2_groups_assigns_auth_group(db, backend):
    user = User.objects.create_user(username='d2-user-001')
    backend._sync_d2_groups(user, {'groups': ['d2:viewer']})
    assert user.groups.filter(name='d2:viewer').exists()


def test_sync_d2_groups_ignores_d1_groups(db, backend):
    user = User.objects.create_user(username='d2-user-002')
    backend._sync_d2_groups(user, {'groups': ['d1:admin', 'd2:editor']})
    assert not user.groups.filter(name='d1:admin').exists()
    assert user.groups.filter(name='d2:editor').exists()


def test_sync_d2_groups_clears_removed_groups(db, backend):
    from django.contrib.auth.models import Group
    user = User.objects.create_user(username='d2-user-003')
    g, _ = Group.objects.get_or_create(name='d2:viewer')
    user.groups.add(g)
    backend._sync_d2_groups(user, {'groups': []})
    assert not user.groups.filter(name='d2:viewer').exists()


def test_sync_ignores_non_prefixed_groups(db, backend):
    user = User.objects.create_user(username='d2-user-004')
    backend._sync_d2_groups(user, {'groups': ['team-a', 'ops', 'd2:admin']})
    assert not user.groups.filter(name='team-a').exists()
    assert not user.groups.filter(name='ops').exists()
    assert user.groups.filter(name='d2:admin').exists()


def test_create_user_syncs_d2_groups(db, backend):
    claims = {
        'sub': 'd2-new-001',
        'email': 'new@d2.com',
        'groups': ['d2:admin'],
    }
    with patch.object(backend, 'get_userinfo', return_value=claims):
        user = backend.create_user(claims)
    assert user.groups.filter(name='d2:admin').exists()


def test_update_user_syncs_d2_groups(db, backend):
    user = User.objects.create_user(username='d2-update-001')
    backend.update_user(user, {'groups': ['d2:editor']})
    assert user.groups.filter(name='d2:editor').exists()
