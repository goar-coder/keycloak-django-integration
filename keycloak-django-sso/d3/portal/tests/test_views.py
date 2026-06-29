import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client

from accounts.models import UserProfile

User = get_user_model()


def _make_user(db, username, groups=()):
    user = User.objects.create_user(username=username, email=f'{username}@example.com')
    UserProfile.objects.create(user=user, sub=username)
    for name in groups:
        g, _ = Group.objects.get_or_create(name=name)
        user.groups.add(g)
    return user


def test_home_redirects_unauthenticated(db):
    resp = Client().get('/')
    assert resp.status_code == 302


def test_home_accessible_when_authenticated(db):
    user = _make_user(db, 'd3-home-user')
    c = Client()
    c.force_login(user)
    resp = c.get('/')
    assert resp.status_code == 200


def test_normas_redirects_unauthenticated(db):
    resp = Client().get('/normas/')
    assert resp.status_code == 302


def test_normas_accessible_with_group(db):
    user = _make_user(db, 'd3-normas-user', groups=['d3:normas'])
    c = Client()
    c.force_login(user)
    resp = c.get('/normas/')
    assert resp.status_code == 200


def test_normas_denied_without_group(db):
    user = _make_user(db, 'd3-normas-no-grp')
    c = Client()
    c.force_login(user)
    resp = c.get('/normas/')
    assert resp.status_code == 302
    assert '/access-denied/' in resp['Location']


def test_documentos_accessible_with_group(db):
    user = _make_user(db, 'd3-docs-user', groups=['d3:documentos'])
    c = Client()
    c.force_login(user)
    resp = c.get('/documentos/')
    assert resp.status_code == 200


def test_documentos_denied_without_group(db):
    user = _make_user(db, 'd3-docs-no-grp')
    c = Client()
    c.force_login(user)
    resp = c.get('/documentos/')
    assert resp.status_code == 302
    assert '/access-denied/' in resp['Location']


def test_leyes_accessible_with_group(db):
    user = _make_user(db, 'd3-leyes-user', groups=['d3:leyes'])
    c = Client()
    c.force_login(user)
    resp = c.get('/leyes/')
    assert resp.status_code == 200


def test_leyes_denied_without_group(db):
    user = _make_user(db, 'd3-leyes-no-grp')
    c = Client()
    c.force_login(user)
    resp = c.get('/leyes/')
    assert resp.status_code == 302
    assert '/access-denied/' in resp['Location']


def test_access_denied_page_shows_required_group(db):
    user = _make_user(db, 'd3-denied-user')
    c = Client()
    c.force_login(user)
    resp = c.get('/access-denied/?required=d3:normas')
    assert resp.status_code == 200
    assert b'd3:normas' in resp.content


def test_user_with_all_groups_can_access_all_routes(db):
    user = _make_user(db, 'd3-all-user', groups=['d3:normas', 'd3:documentos', 'd3:leyes'])
    c = Client()
    c.force_login(user)
    assert c.get('/normas/').status_code == 200
    assert c.get('/documentos/').status_code == 200
    assert c.get('/leyes/').status_code == 200


def test_admin_group_can_access_all_routes(db):
    user = _make_user(db, 'd3-admin-user', groups=['d3:admin'])
    c = Client()
    c.force_login(user)
    assert c.get('/normas/').status_code == 200
    assert c.get('/documentos/').status_code == 200
    assert c.get('/leyes/').status_code == 200


def test_admin_group_shows_all_sections_on_home(db):
    user = _make_user(db, 'd3-admin-home', groups=['d3:admin'])
    c = Client()
    c.force_login(user)
    resp = c.get('/')
    assert resp.status_code == 200
    assert resp.context['has_normas'] is True
    assert resp.context['has_documentos'] is True
    assert resp.context['has_leyes'] is True
