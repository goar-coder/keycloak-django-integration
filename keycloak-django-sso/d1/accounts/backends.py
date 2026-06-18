import logging

from django.contrib.auth.models import Group
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from accounts.models import UserProfile

logger = logging.getLogger('accounts')

_SYSTEM_ROLES = frozenset({'uma_authorization', 'offline_access'})


class KeycloakOIDCBackend(OIDCAuthenticationBackend):

    def create_user(self, claims):
        sub = claims.get('sub', '')
        email = claims.get('email', '')
        user = super().create_user(claims)
        user.set_unusable_password()
        user.save(update_fields=['password'])
        UserProfile.objects.get_or_create(
            user=user,
            defaults={'sub': sub, 'email': email},
        )
        logger.info('action=oidc_user_created sub=%s email=%s', sub, email)
        self.update_user(user, claims)
        return user

    def update_user(self, user, claims):
        sub = claims.get('sub', user.username)
        email = claims.get('email', '')
        raw_roles = claims.get('realm_access', {}).get('roles', [])
        roles = [r for r in raw_roles if r not in _SYSTEM_ROLES and not r.startswith('default-roles')]
        groups = claims.get('groups', [])

        UserProfile.objects.filter(user=user).update(
            email=email,
            roles=roles,
            groups=groups,
        )

        d1_group_names = [g for g in groups if g.startswith('d1:') or g.startswith('admin:')]
        django_groups = []
        for name in d1_group_names:
            group, _ = Group.objects.get_or_create(name=name)
            django_groups.append(group)
        user.groups.set(django_groups)

        logger.info(
            'action=oidc_profile_synced sub=%s roles_count=%d groups_count=%d d1_groups=%s',
            sub, len(roles), len(groups), d1_group_names,
        )
        return user
