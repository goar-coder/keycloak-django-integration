import pytest
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()


def test_health_returns_200():
    assert Client().get('/health/').status_code == 200


def test_logout_redirects(db):
    user = User.objects.create_user(username='logoutuser')
    c = Client()
    c.force_login(user)
    response = c.get('/logout/')
    assert response.status_code == 302
