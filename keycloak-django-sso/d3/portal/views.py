import logging
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from accounts.decorators import require_groups

logger = logging.getLogger('portal')


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user_groups = set(self.request.user.groups.values_list('name', flat=True))
        is_admin = 'd3:admin' in user_groups
        ctx['has_normas'] = is_admin or 'd3:normas' in user_groups
        ctx['has_documentos'] = is_admin or 'd3:documentos' in user_groups
        ctx['has_leyes'] = is_admin or 'd3:leyes' in user_groups
        return ctx


@method_decorator(require_groups(['d3:normas', 'd3:admin']), name='dispatch')
class NormasView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/normas.html'


@method_decorator(require_groups(['d3:documentos', 'd3:admin']), name='dispatch')
class DocumentosView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/documentos.html'


@method_decorator(require_groups(['d3:leyes', 'd3:admin']), name='dispatch')
class LeyesView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/leyes.html'


class AccessDeniedView(TemplateView):
    template_name = 'portal/access_denied.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['required_group'] = self.request.GET.get('required', '')
        return ctx
