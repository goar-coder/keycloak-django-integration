from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect


class ScopeRequiredMixin(LoginRequiredMixin):
    required_scope = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.required_scope:
            user_scopes = request.session.get('oidc_scopes', [])
            if self.required_scope not in user_scopes:
                return redirect(f'/denied/?required={self.required_scope}')
        return super().dispatch(request, *args, **kwargs)
