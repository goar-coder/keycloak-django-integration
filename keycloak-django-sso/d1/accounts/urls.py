from django.urls import path
from accounts.views import HealthView, LogoutView, ProfileView

urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
