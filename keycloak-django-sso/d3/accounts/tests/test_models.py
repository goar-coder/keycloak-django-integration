import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from accounts.models import UserProfile

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='test-sub-d3-001', email='test@example.com')


def test_userprofile_sub_uniqueness(db, user):
    UserProfile.objects.create(user=user, sub='unique-d3-sub')
    user2 = User.objects.create_user(username='other-d3-user', email='other@example.com')
    with pytest.raises(IntegrityError):
        UserProfile.objects.create(user=user2, sub='unique-d3-sub')


def test_userprofile_roles_default_empty(db, user):
    profile = UserProfile.objects.create(user=user, sub='sub-d3-roles')
    assert profile.roles == []


def test_userprofile_groups_default_empty(db, user):
    profile = UserProfile.objects.create(user=user, sub='sub-d3-groups')
    assert profile.groups == []


def test_userprofile_str_returns_sub(db, user):
    profile = UserProfile.objects.create(user=user, sub='sub-d3-str')
    assert str(profile) == 'sub-d3-str'


def test_userprofile_cascade_delete(db, user):
    UserProfile.objects.create(user=user, sub='sub-d3-cascade')
    user.delete()
    assert not UserProfile.objects.filter(sub='sub-d3-cascade').exists()
