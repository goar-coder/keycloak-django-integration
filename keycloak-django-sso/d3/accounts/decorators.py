import logging
from functools import wraps

from django.conf import settings
from django.shortcuts import redirect

logger = logging.getLogger('accounts')


def require_groups(allowed_groups):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")
            if not request.user.groups.filter(name__in=allowed_groups).exists():
                required = ','.join(allowed_groups)
                logger.info(
                    'action=group_denied user=%s required=%s',
                    request.user.username, required,
                )
                return redirect(f'/access-denied/?required={required}')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
