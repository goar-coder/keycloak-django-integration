import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.http import HttpResponse
from django.test import RequestFactory

from accounts.decorators import require_groups

User = get_user_model()


@pytest.fixture
def rf():
    return RequestFactory()


def _ok_view(request):
    return HttpResponse('ok', status=200)


def test_require_groups_allows_user_with_matching_group(rf, db):
    user = User.objects.create_user(username='grp-user-d2')
    g, _ = Group.objects.get_or_create(name='d2:viewer')
    user.groups.add(g)
    request = rf.get('/reports/')
    request.user = user
    assert require_groups(['d2:viewer'])(_ok_view)(request).status_code == 200


def test_require_groups_denies_user_without_group(rf, db):
    user = User.objects.create_user(username='no-grp-d2')
    request = rf.get('/reports/')
    request.user = user
    response = require_groups(['d2:viewer'])(_ok_view)(request)
    assert response.status_code == 302
    assert '/group-denied/' in response['Location']
    assert 'd2:viewer' in response['Location']


def test_require_groups_redirects_unauthenticated(rf, db):
    request = rf.get('/editor/')
    request.user = AnonymousUser()
    response = require_groups(['d2:editor'])(_ok_view)(request)
    assert response.status_code == 302
    assert 'oidc/authenticate' in response['Location'] or 'login' in response['Location'].lower()


def test_require_groups_or_logic_allows_any(rf, db):
    user = User.objects.create_user(username='editor-user')
    g, _ = Group.objects.get_or_create(name='d2:editor')
    user.groups.add(g)
    request = rf.get('/editor/')
    request.user = user
    assert require_groups(['d2:editor', 'd2:admin'])(_ok_view)(request).status_code == 200
