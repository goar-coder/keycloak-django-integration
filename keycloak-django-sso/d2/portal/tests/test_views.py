import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client

User = get_user_model()


def _client_with_groups(db, group_names):
    key = '-'.join(sorted(group_names)) or 'nogroup'
    user = User.objects.create_user(username=f'u-{key[:30]}')
    for name in group_names:
        g, _ = Group.objects.get_or_create(name=name)
        user.groups.add(g)
    c = Client()
    c.force_login(user)
    return c


# --- HomeView ---

def test_home_redirects_unauthenticated():
    assert Client().get('/').status_code == 302


def test_home_accessible_when_authenticated(db):
    assert _client_with_groups(db, []).get('/').status_code == 200


def test_home_context_has_d2_groups(db):
    c = _client_with_groups(db, ['d2:viewer'])
    resp = c.get('/')
    assert 'd2:viewer' in resp.context['d2_groups']


# --- ReportsView (requires d2:report) ---

def test_reports_accessible_with_report_group(db):
    assert _client_with_groups(db, ['d2:report']).get('/reports/').status_code == 200


def test_reports_denied_for_viewer(db):
    resp = _client_with_groups(db, ['d2:viewer']).get('/reports/')
    assert resp.status_code == 302
    assert '/group-denied/' in resp['Location']


def test_reports_denied_for_editor(db):
    resp = _client_with_groups(db, ['d2:editor']).get('/reports/')
    assert resp.status_code == 302
    assert '/group-denied/' in resp['Location']


def test_reports_denied_without_group(db):
    resp = _client_with_groups(db, []).get('/reports/')
    assert resp.status_code == 302
    assert '/group-denied/' in resp['Location']


def test_reports_redirects_anonymous():
    assert Client().get('/reports/').status_code == 302


# --- DataView (requires d2:data) ---

def test_data_accessible_with_data_group(db):
    assert _client_with_groups(db, ['d2:data']).get('/data/').status_code == 200


def test_data_accessible_with_d2_admin_group(db):
    assert _client_with_groups(db, ['d2:admin']).get('/data/').status_code == 200


def test_data_accessible_with_admin_data_group(db):
    assert _client_with_groups(db, ['admin:data']).get('/data/').status_code == 200


def test_data_denied_for_viewer(db):
    resp = _client_with_groups(db, ['d2:viewer']).get('/data/')
    assert resp.status_code == 302
    assert '/group-denied/' in resp['Location']


def test_data_denied_for_editor(db):
    resp = _client_with_groups(db, ['d2:editor']).get('/data/')
    assert resp.status_code == 302
    assert '/group-denied/' in resp['Location']


def test_data_denied_without_group(db):
    resp = _client_with_groups(db, []).get('/data/')
    assert resp.status_code == 302
    assert '/group-denied/' in resp['Location']


# --- GroupAccessDeniedView ---

def test_group_denied_shows_required_groups(db):
    c = _client_with_groups(db, [])
    resp = c.get('/group-denied/?required=d2:editor,d2:admin')
    assert resp.status_code == 200
    assert 'd2:editor' in resp.context['required_groups']


# --- EditorView (requires d2:editor or d2:admin) ---

def test_editor_accessible_with_editor(db):
    assert _client_with_groups(db, ['d2:editor']).get('/editor/').status_code == 200


def test_editor_accessible_with_admin(db):
    assert _client_with_groups(db, ['d2:admin']).get('/editor/').status_code == 200


def test_editor_denied_for_viewer(db):
    resp = _client_with_groups(db, ['d2:viewer']).get('/editor/')
    assert resp.status_code == 302
    assert '/group-denied/' in resp['Location']


def test_editor_redirects_anonymous():
    assert Client().get('/editor/').status_code == 302


# --- D2AdminView (requires d2:admin only) ---

def test_d2admin_accessible_with_admin(db):
    assert _client_with_groups(db, ['d2:admin']).get('/admin/').status_code == 200


def test_d2admin_denied_for_editor(db):
    resp = _client_with_groups(db, ['d2:editor']).get('/admin/')
    assert resp.status_code == 302
    assert '/group-denied/' in resp['Location']


def test_d2admin_denied_for_viewer(db):
    resp = _client_with_groups(db, ['d2:viewer']).get('/admin/')
    assert resp.status_code == 302
    assert '/group-denied/' in resp['Location']


def test_d2admin_redirects_anonymous():
    assert Client().get('/admin/').status_code == 302
