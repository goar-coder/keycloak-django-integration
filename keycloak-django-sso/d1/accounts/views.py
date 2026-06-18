import logging

from django.contrib.auth import logout
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

logger = logging.getLogger('accounts')


class HealthView(View):
    def get(self, request):
        return JsonResponse({'status': 'ok'})


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['profile'] = self.request.user.profile
        return ctx


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
