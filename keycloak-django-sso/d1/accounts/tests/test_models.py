import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from accounts.models import UserProfile

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='test-sub-001', email='test@example.com', password=None)


@pytest.fixture
def profile(user):
    return UserProfile.objects.create(user=user, sub='test-sub-001', email='test@example.com')


def test_userprofile_sub_uniqueness(db, user):
    UserProfile.objects.create(user=user, sub='unique-sub')
    user2 = User.objects.create_user(username='other-user', email='other@example.com')
    with pytest.raises(IntegrityError):
        UserProfile.objects.create(user=user2, sub='unique-sub')


def test_userprofile_roles_default_empty(db, user):
    profile = UserProfile.objects.create(user=user, sub='sub-roles')
    assert profile.roles == []


def test_userprofile_groups_default_empty(db, user):
    profile = UserProfile.objects.create(user=user, sub='sub-groups')
    assert profile.groups == []


def test_userprofile_str_returns_sub(profile):
    assert str(profile) == 'test-sub-001'


def test_userprofile_cascade_delete(db, user):
    UserProfile.objects.create(user=user, sub='sub-cascade')
    user_id = user.pk
    user.delete()
    assert not UserProfile.objects.filter(sub='sub-cascade').exists()
