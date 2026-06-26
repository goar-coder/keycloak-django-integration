from django.urls import path, include
from accounts.views import MagicLinkCallbackView

urlpatterns = [
    # Override callback before the include so magic-link state injection takes effect
    path('oidc/callback/', MagicLinkCallbackView.as_view(), name='oidc_authentication_callback'),
    path('oidc/', include('mozilla_django_oidc.urls')),
    path('', include('accounts.urls')),
    path('', include('portal.urls')),
]
