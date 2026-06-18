import logging

from django.contrib.auth.models import Group
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger('accounts')


class D2OIDCBackend(OIDCAuthenticationBackend):

    def _sync_d2_groups(self, user, claims):
        d2_group_names = [g for g in claims.get('groups', []) if g.startswith('d2:') or g.startswith('admin:')]
        django_groups = []
        for name in d2_group_names:
            group, _ = Group.objects.get_or_create(name=name)
            django_groups.append(group)
        user.groups.set(django_groups)
        logger.info('action=d2_groups_synced user=%s d2_groups=%s', user.username, d2_group_names)

    def create_user(self, claims):
        user = super().create_user(claims)
        user.set_unusable_password()
        user.save(update_fields=['password'])
        self._sync_d2_groups(user, claims)
        return user

    def update_user(self, user, claims):
        self._sync_d2_groups(user, claims)
        return user
