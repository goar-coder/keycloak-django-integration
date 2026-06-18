from django.urls import path
from accounts.views import HealthView, LogoutView

urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
