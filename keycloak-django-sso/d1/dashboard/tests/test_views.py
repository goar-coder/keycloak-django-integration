import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client

from accounts.models import UserProfile

User = get_user_model()


@pytest.fixture
def anon_client():
    return Client()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='sub-001', email='alice@example.com')
    UserProfile.objects.create(user=user, sub='sub-001', email='alice@example.com', roles=['admin'], groups=['team-a'])
    c = Client()
    c.force_login(user)
    return c


def _client_with_groups(db, group_names):
    username = 'user-' + '-'.join(group_names) if group_names else 'user-nogroup'
    user = User.objects.create_user(username=username)
    UserProfile.objects.get_or_create(user=user, defaults={'sub': username, 'email': f'{username}@test.com'})
    for name in group_names:
        g, _ = Group.objects.get_or_create(name=name)
        user.groups.add(g)
    c = Client()
    c.force_login(user)
    return c


def test_dashboard_redirects_unauthenticated(anon_client):
    resp = anon_client.get('/dashboard/')
    assert resp.status_code == 302
    assert '/oidc/authenticate/' in resp['Location']


def test_dashboard_accessible_when_authenticated(auth_client):
    resp = auth_client.get('/dashboard/')
    assert resp.status_code == 200


def test_dashboard_context_has_profile(auth_client):
    resp = auth_client.get('/dashboard/')
    assert 'profile' in resp.context
    assert resp.context['profile'].roles == ['admin']
    assert resp.context['profile'].groups == ['team-a']


# --- GroupAccessDeniedView ---

def test_access_denied_shows_required_groups(db):
    c = _client_with_groups(db, [])
    resp = c.get('/access-denied/?required=d1:rrhh,d1:admin')
    assert resp.status_code == 200
    assert 'd1:rrhh' in resp.context['required_groups']
    assert 'd1:admin' in resp.context['required_groups']


# --- RRHHView (requires d1:rrhh or d1:admin) ---

def test_rrhh_accessible_with_rrhh_group(db):
    assert _client_with_groups(db, ['d1:rrhh']).get('/rrhh/').status_code == 200


def test_rrhh_accessible_with_admin_group(db):
    assert _client_with_groups(db, ['d1:admin']).get('/rrhh/').status_code == 200


def test_rrhh_denied_for_worker(db):
    resp = _client_with_groups(db, ['d1:worker']).get('/rrhh/')
    assert resp.status_code == 302
    assert '/access-denied/' in resp['Location']


def test_rrhh_redirects_anonymous(anon_client):
    assert anon_client.get('/rrhh/').status_code == 302


# --- WorkerView (requires d1:worker or d1:admin) ---

def test_worker_accessible_with_worker_group(db):
    assert _client_with_groups(db, ['d1:worker']).get('/worker/').status_code == 200


def test_worker_accessible_with_admin_group(db):
    assert _client_with_groups(db, ['d1:admin']).get('/worker/').status_code == 200


def test_worker_denied_for_rrhh_only(db):
    resp = _client_with_groups(db, ['d1:rrhh']).get('/worker/')
    assert resp.status_code == 302
    assert '/access-denied/' in resp['Location']


def test_worker_redirects_anonymous(anon_client):
    assert anon_client.get('/worker/').status_code == 302


# --- D1AdminView (requires d1:admin only) ---

def test_d1admin_accessible_with_admin_group(db):
    assert _client_with_groups(db, ['d1:admin']).get('/admin/').status_code == 200


def test_d1admin_denied_for_worker(db):
    resp = _client_with_groups(db, ['d1:worker']).get('/admin/')
    assert resp.status_code == 302
    assert '/access-denied/' in resp['Location']


def test_d1admin_denied_for_rrhh(db):
    resp = _client_with_groups(db, ['d1:rrhh']).get('/admin/')
    assert resp.status_code == 302
    assert '/access-denied/' in resp['Location']


def test_d1admin_redirects_anonymous(anon_client):
    assert anon_client.get('/admin/').status_code == 302


# --- D1HomeView (requires any d1:* group) ---

def test_d1home_accessible_for_rrhh(db):
    assert _client_with_groups(db, ['d1:rrhh']).get('/home/').status_code == 200


def test_d1home_accessible_for_worker(db):
    assert _client_with_groups(db, ['d1:worker']).get('/home/').status_code == 200


def test_d1home_accessible_for_admin(db):
    assert _client_with_groups(db, ['d1:admin']).get('/home/').status_code == 200


def test_d1home_denied_without_d1_groups(db):
    resp = _client_with_groups(db, []).get('/home/')
    assert resp.status_code == 302
    assert '/access-denied/' in resp['Location']


def test_d1home_redirects_anonymous(anon_client):
    assert anon_client.get('/home/').status_code == 302


# --- DataView (requires d1:data or d1:admin) ---

def test_data_accessible_with_data_group(db):
    assert _client_with_groups(db, ['d1:data']).get('/data/').status_code == 200


def test_data_accessible_with_admin_group(db):
    assert _client_with_groups(db, ['d1:admin']).get('/data/').status_code == 200


def test_data_accessible_with_admin_data_group(db):
    assert _client_with_groups(db, ['admin:data']).get('/data/').status_code == 200


def test_data_denied_for_worker(db):
    resp = _client_with_groups(db, ['d1:worker']).get('/data/')
    assert resp.status_code == 302
    assert '/access-denied/' in resp['Location']


def test_data_denied_for_rrhh(db):
    resp = _client_with_groups(db, ['d1:rrhh']).get('/data/')
    assert resp.status_code == 302
    assert '/access-denied/' in resp['Location']


def test_data_denied_without_group(db):
    resp = _client_with_groups(db, []).get('/data/')
    assert resp.status_code == 302
    assert '/access-denied/' in resp['Location']


def test_data_redirects_anonymous(anon_client):
    assert anon_client.get('/data/').status_code == 302
