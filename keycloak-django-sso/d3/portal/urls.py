from django.urls import path
from portal.views import (
    AccessDeniedView,
    DocumentosView,
    HomeView,
    LeyesView,
    NormasView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('normas/', NormasView.as_view(), name='normas'),
    path('documentos/', DocumentosView.as_view(), name='documentos'),
    path('leyes/', LeyesView.as_view(), name='leyes'),
    path('access-denied/', AccessDeniedView.as_view(), name='access-denied'),
]
