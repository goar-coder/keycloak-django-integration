from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from accounts.decorators import require_groups
from dashboard.forms import UserProvisionForm
from kc_admin.client import (
    DuplicateUser,
    GroupNotFound,
    KeycloakConnectionError,
    RoleNotFound,
)
from kc_admin.views import kc_client


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


@method_decorator(require_groups(['d1:admin']), name='dispatch')
class UserProvisionView(LoginRequiredMixin, View):
    template_name = 'dashboard/provision_user.html'

    def _get_role_choices(self):
        try:
            roles = kc_client.list_assignable_roles()
            choices = []
            for r in roles:
                if r['type'] == 'client':
                    value = f"client:{r['client']}:{r['name']}"
                    label = f"[{r['client']}] {r['name']}"
                else:
                    value = f"realm::{r['name']}"
                    label = f"[realm] {r['name']}"
                choices.append((value, label))
            return choices
        except KeycloakConnectionError:
            return []

    def get(self, request):
        role_choices = self._get_role_choices()
        form = UserProvisionForm(role_choices=role_choices)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        role_choices = self._get_role_choices()
        form = UserProvisionForm(request.POST, role_choices=role_choices)
        ctx = {'form': form}

        if not form.is_valid():
            return render(request, self.template_name, ctx)

        data = form.cleaned_data
        warnings = []

        try:
            user_id = kc_client.provision_user(
                email=data['email'],
                username=data['username'],
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
            )
        except DuplicateUser:
            form.add_error(None, 'A user with this username or email already exists in Keycloak.')
            return render(request, self.template_name, ctx)
        except KeycloakConnectionError:
            form.add_error(None, 'Unable to reach identity provider. Please try again.')
            return render(request, self.template_name, ctx)

        for group_name in data.get('groups', []):
            try:
                kc_client.assign_group(user_id, group_name)
            except (GroupNotFound, KeycloakConnectionError) as exc:
                warnings.append(f'Could not assign group "{group_name}": {exc}')

        if data.get('role'):
            role_type, role_client, role_name = data['role'].split(':', 2)
            try:
                if role_type == 'client':
                    kc_client.assign_client_role(user_id, role_client, role_name)
                else:
                    kc_client.assign_realm_role(user_id, role_name)
            except (RoleNotFound, KeycloakConnectionError) as exc:
                warnings.append(f'Could not assign role "{role_name}": {exc}')

        email_sent = True
        try:
            kc_client.send_activation_email(user_id)
        except KeycloakConnectionError:
            email_sent = False
            warnings.append(
                f'Activation email could not be sent to {data["email"]}. '
                'The user was created — resend manually from Keycloak.'
            )

        ctx = {
            'success': True,
            'success_email': data['email'],
            'success_username': data['username'],
            'email_sent': email_sent,
            'warnings': warnings,
            'form': UserProvisionForm(role_choices=role_choices),
        }
        return render(request, self.template_name, ctx)
