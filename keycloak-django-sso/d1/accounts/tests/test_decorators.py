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
    user = User.objects.create_user(username='grp-user')
    g, _ = Group.objects.get_or_create(name='d1:rrhh')
    user.groups.add(g)
    request = rf.get('/rrhh/')
    request.user = user
    response = require_groups(['d1:rrhh'])(_ok_view)(request)
    assert response.status_code == 200


def test_require_groups_denies_user_without_group(rf, db):
    user = User.objects.create_user(username='no-grp-user')
    request = rf.get('/rrhh/')
    request.user = user
    response = require_groups(['d1:rrhh'])(_ok_view)(request)
    assert response.status_code == 302
    assert '/access-denied/' in response['Location']
    assert 'd1:rrhh' in response['Location']


def test_require_groups_redirects_unauthenticated(rf, db):
    request = rf.get('/rrhh/')
    request.user = AnonymousUser()
    response = require_groups(['d1:rrhh'])(_ok_view)(request)
    assert response.status_code == 302
    assert 'oidc/authenticate' in response['Location'] or 'login' in response['Location'].lower()


def test_require_groups_or_logic_allows_any_matching(rf, db):
    user = User.objects.create_user(username='worker-user')
    g, _ = Group.objects.get_or_create(name='d1:worker')
    user.groups.add(g)
    request = rf.get('/worker/')
    request.user = user
    response = require_groups(['d1:worker', 'd1:admin'])(_ok_view)(request)
    assert response.status_code == 200
