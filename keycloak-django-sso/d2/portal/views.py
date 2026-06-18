from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from accounts.decorators import require_groups


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['d2_groups'] = [g.name for g in self.request.user.groups.filter(name__startswith='d2:')]
        return ctx


class GroupAccessDeniedView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/group_access_denied.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        raw = self.request.GET.get('required', '')
        ctx['required_groups'] = [g for g in raw.split(',') if g]
        return ctx


@method_decorator(require_groups(['d2:report']), name='dispatch')
class ReportsView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/reports.html'


@method_decorator(require_groups(['d2:data', 'd2:admin', 'admin:data']), name='dispatch')
class DataView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/data.html'


@method_decorator(require_groups(['d2:editor', 'd2:admin']), name='dispatch')
class EditorView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/editor.html'


@method_decorator(require_groups(['d2:admin']), name='dispatch')
class D2AdminView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/admin_section.html'
