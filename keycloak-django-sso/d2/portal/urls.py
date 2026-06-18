from django.urls import path

from portal.views import D2AdminView, DataView, EditorView, GroupAccessDeniedView, HomeView, ReportsView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('reports/', ReportsView.as_view(), name='reports'),
    path('data/', DataView.as_view(), name='data'),
    path('editor/', EditorView.as_view(), name='editor'),
    path('admin/', D2AdminView.as_view(), name='d2-admin'),
    path('group-denied/', GroupAccessDeniedView.as_view(), name='group-access-denied'),
]
