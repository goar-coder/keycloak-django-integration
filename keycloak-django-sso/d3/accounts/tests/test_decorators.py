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
    user = User.objects.create_user(username='d3-grp-user')
    g, _ = Group.objects.get_or_create(name='d3:normas')
    user.groups.add(g)
    request = rf.get('/normas/')
    request.user = user
    response = require_groups(['d3:normas'])(_ok_view)(request)
    assert response.status_code == 200


def test_require_groups_denies_user_without_group(rf, db):
    user = User.objects.create_user(username='d3-no-grp-user')
    request = rf.get('/normas/')
    request.user = user
    response = require_groups(['d3:normas'])(_ok_view)(request)
    assert response.status_code == 302
    assert '/access-denied/' in response['Location']
    assert 'd3:normas' in response['Location']


def test_require_groups_redirects_unauthenticated(rf):
    request = rf.get('/normas/')
    request.user = AnonymousUser()
    response = require_groups(['d3:normas'])(_ok_view)(request)
    assert response.status_code == 302
    assert 'oidc/authenticate' in response['Location'] or 'login' in response['Location'].lower()


def test_require_groups_allows_any_matching_group(rf, db):
    user = User.objects.create_user(username='d3-multi-grp-user')
    g, _ = Group.objects.get_or_create(name='d3:leyes')
    user.groups.add(g)
    request = rf.get('/leyes/')
    request.user = user
    response = require_groups(['d3:leyes', 'd3:normas'])(_ok_view)(request)
    assert response.status_code == 200
