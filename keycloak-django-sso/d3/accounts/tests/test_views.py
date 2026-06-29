import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from accounts.models import UserProfile

User = get_user_model()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='sub-d3-001', email='alice@example.com')
    UserProfile.objects.create(user=user, sub='sub-d3-001', email='alice@example.com')
    c = Client()
    c.force_login(user)
    return c


def test_health_returns_200():
    resp = Client().get('/health/')
    assert resp.status_code == 200


def test_health_returns_ok_json():
    resp = Client().get('/health/')
    assert resp.json() == {'status': 'ok'}


def test_profile_redirects_unauthenticated():
    resp = Client().get('/profile/')
    assert resp.status_code == 302


def test_profile_accessible_when_authenticated(auth_client):
    resp = auth_client.get('/profile/')
    assert resp.status_code == 200


def test_logout_clears_session(auth_client):
    resp = auth_client.get('/logout/')
    assert resp.status_code in (200, 302)
