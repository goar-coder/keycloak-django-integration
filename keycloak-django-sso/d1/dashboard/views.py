from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from accounts.decorators import require_groups


class HomeView(TemplateView):
    template_name = 'dashboard/home.html'


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['profile'] = self.request.user.profile
        return ctx


class AdminPanelView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/admin_panel.html'


class GroupAccessDeniedView(TemplateView):
    template_name = 'dashboard/access_denied.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        raw = self.request.GET.get('required', '')
        ctx['required_groups'] = [g for g in raw.split(',') if g]
        return ctx


@method_decorator(require_groups(['d1:rrhh', 'd1:worker', 'd1:data', 'd1:admin']), name='dispatch')
class D1HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home_groups.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['profile'] = self.request.user.profile
        ctx['d1_groups'] = [g.name for g in self.request.user.groups.filter(name__startswith='d1:')]
        return ctx


@method_decorator(require_groups(['d1:rrhh', 'd1:admin']), name='dispatch')
class RRHHView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/rrhh.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['profile'] = self.request.user.profile
        return ctx


@method_decorator(require_groups(['d1:worker', 'd1:admin']), name='dispatch')
class WorkerView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/worker.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['profile'] = self.request.user.profile
        return ctx


@method_decorator(require_groups(['d1:admin']), name='dispatch')
class D1AdminView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/admin_section.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['profile'] = self.request.user.profile
        return ctx


@method_decorator(require_groups(['d1:data', 'd1:admin', 'admin:data']), name='dispatch')
class DataView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/data.html'
