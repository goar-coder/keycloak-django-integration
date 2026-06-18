from django.urls import path
from kc_admin import views

urlpatterns = [
    path('users/', views.users_list, name='users-list'),
    path('users/create/', views.users_create, name='users-create'),
    path('users/<str:sub>/roles/assign/', views.users_assign_role, name='users-assign-role'),
    path('users/<str:sub>/groups/assign/', views.users_assign_group, name='users-assign-group'),
    path('users/<str:sub>/deactivate/', views.users_deactivate, name='users-deactivate'),
    path('roles/', views.roles_list, name='roles-list'),
    path('groups/', views.groups_list, name='groups-list'),
]
