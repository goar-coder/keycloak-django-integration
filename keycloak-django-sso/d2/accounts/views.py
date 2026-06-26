import logging

from django.contrib.auth import logout
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View

from mozilla_django_oidc.views import OIDCAuthenticationCallbackView

logger = logging.getLogger('accounts')


class MagicLinkCallbackView(OIDCAuthenticationCallbackView):
    """
    Handles /oidc/callback/ for both password and magic-link flows.

    When a magic link is opened in a new browser context (e.g. the email client
    opens the link in a regular window while the original auth was in incognito),
    the Django session will not contain the OIDC state generated during the
    initial auth request. This view injects the incoming state so the standard
    callback can proceed. Nonce validation is disabled via OIDC_USE_NONCE=False.
    """
    def get(self, request):
        state = request.GET.get("state", "")
        if state and (
            "oidc_states" not in request.session
            or state not in request.session.get("oidc_states", {})
        ):
            existing = request.session.get("oidc_states", {})
            existing[state] = {"nonce": None, "code_verifier": None}
            request.session["oidc_states"] = existing
            request.session.modified = True
        return super().get(request)


class HealthView(View):
    def get(self, request):
        return JsonResponse({'status': 'ok'})


class LogoutView(View):
    def get(self, request):
        logout_endpoint = getattr(settings, 'OIDC_OP_LOGOUT_ENDPOINT', None)
        id_token = request.session.get('oidc_id_token')
        logout(request)
        logger.info('action=oidc_logout')
        if logout_endpoint and id_token:
            redirect_uri = request.build_absolute_uri('/')
            return redirect(
                f"{logout_endpoint}?id_token_hint={id_token}&post_logout_redirect_uri={redirect_uri}"
            )
        return redirect('/')
