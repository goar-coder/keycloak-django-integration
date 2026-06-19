from django.urls import path

from dashboard.views import (
    AdminPanelView,
    D1AdminView,
    D1HomeView,
    DataView,
    DashboardView,
    GroupAccessDeniedView,
    HomeView,
    RRHHView,
    UserProvisionView,
    WorkerView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('admin-panel/', AdminPanelView.as_view(), name='admin-panel'),
    path('access-denied/', GroupAccessDeniedView.as_view(), name='group-access-denied'),
    path('home/', D1HomeView.as_view(), name='d1-home'),
    path('rrhh/', RRHHView.as_view(), name='rrhh'),
    path('worker/', WorkerView.as_view(), name='worker'),
    path('admin/', D1AdminView.as_view(), name='d1-admin'),
    path('data/', DataView.as_view(), name='d1-data'),
    path('provision/', UserProvisionView.as_view(), name='provision-user'),
]
