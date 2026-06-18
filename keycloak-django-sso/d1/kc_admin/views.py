import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from kc_admin.client import (
    KeycloakAdminClient,
    DuplicateUser,
    GroupNotFound,
    KeycloakConnectionError,
    RoleNotFound,
    UserNotFound,
)

logger = logging.getLogger('kc_admin')

kc_client = KeycloakAdminClient()


def _require_auth(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    return None


@require_http_methods(['GET'])
def groups_list(request):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error
    try:
        groups = kc_client.list_groups()
        return JsonResponse({'groups': groups})
    except KeycloakConnectionError:
        return JsonResponse({'error': 'Unable to reach identity provider'}, status=502)


@require_http_methods(['GET'])
def roles_list(request):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error
    try:
        roles = kc_client.list_assignable_roles()
        return JsonResponse({'roles': roles})
    except KeycloakConnectionError:
        return JsonResponse({'error': 'Unable to reach identity provider'}, status=502)


@require_http_methods(['GET'])
def users_list(request):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error
    try:
        users = kc_client.list_users()
        return JsonResponse({'users': users})
    except KeycloakConnectionError as exc:
        return JsonResponse({'error': 'Unable to reach identity provider'}, status=502)


@require_http_methods(['POST'])
def users_create(request):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    email = body.get('email', '').strip()
    username = body.get('username', '').strip()
    password = body.get('password', '').strip()
    if not email or not username or not password:
        return JsonResponse({'error': 'Fields required: email, username, password'}, status=400)

    try:
        user_id = kc_client.create_user(email, username, body.get('first_name', ''), body.get('last_name', ''), password)
        return JsonResponse({'id': user_id, 'email': email, 'username': username}, status=201)
    except DuplicateUser:
        return JsonResponse({'error': 'User with this username or email already exists'}, status=409)
    except KeycloakConnectionError:
        return JsonResponse({'error': 'Unable to reach identity provider'}, status=502)


@require_http_methods(['POST'])
def users_assign_role(request, sub):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    role_name = body.get('role_name', '').strip()
    role_type = body.get('role_type', 'realm')
    role_client = body.get('role_client', '')
    if not role_name:
        return JsonResponse({'error': 'Field required: role_name'}, status=400)

    try:
        if role_type == 'client' and role_client:
            kc_client.assign_client_role(sub, role_client, role_name)
        else:
            kc_client.assign_realm_role(sub, role_name)
        return JsonResponse({'success': True, 'user_id': sub, 'role': role_name, 'type': role_type})
    except (UserNotFound, RoleNotFound):
        return JsonResponse({'error': 'User or role not found'}, status=404)
    except KeycloakConnectionError:
        return JsonResponse({'error': 'Unable to reach identity provider'}, status=502)


@require_http_methods(['POST'])
def users_assign_group(request, sub):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    group_name = body.get('group_name', '').strip()
    if not group_name:
        return JsonResponse({'error': 'Field required: group_name'}, status=400)

    try:
        kc_client.assign_group(sub, group_name)
        return JsonResponse({'success': True, 'user_id': sub, 'group': group_name})
    except (UserNotFound, GroupNotFound):
        return JsonResponse({'error': 'User or group not found'}, status=404)
    except KeycloakConnectionError:
        return JsonResponse({'error': 'Unable to reach identity provider'}, status=502)


@require_http_methods(['POST'])
def users_deactivate(request, sub):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error

    if request.user.username == sub:
        return JsonResponse({'error': 'Cannot deactivate your own account'}, status=409)

    try:
        kc_client.deactivate_user(sub)
        return JsonResponse({'success': True, 'user_id': sub, 'enabled': False})
    except UserNotFound:
        return JsonResponse({'error': 'User not found'}, status=404)
    except KeycloakConnectionError:
        return JsonResponse({'error': 'Unable to reach identity provider'}, status=502)
