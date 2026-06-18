from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

SECRET_KEY = env('D2_SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'mozilla_django_oidc',
    'accounts',
    'portal',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'mozilla_django_oidc.middleware.SessionRefresh',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': env.db('D2_DATABASE_URL')
}

AUTHENTICATION_BACKENDS = [
    'accounts.backends.D2OIDCBackend',
]

# mozilla-django-oidc settings
# _KC_BASE: internal Docker network URL (server-to-server calls)
# _KC_PUBLIC_BASE: public URL visible to the browser (redirects)
_KC_BASE = f"{env('KEYCLOAK_SERVER_URL')}/realms/{env('KEYCLOAK_REALM')}/protocol/openid-connect"
_KC_PUBLIC_BASE = f"{env('KEYCLOAK_PUBLIC_URL', default='http://localhost:8080')}/realms/{env('KEYCLOAK_REALM')}/protocol/openid-connect"
OIDC_RP_CLIENT_ID = env('D2_OIDC_CLIENT_ID', default='d2-client')
OIDC_RP_CLIENT_SECRET = env('D2_OIDC_CLIENT_SECRET')
OIDC_RP_SIGN_ALGO = 'RS256'
OIDC_OP_JWKS_ENDPOINT = f"{_KC_BASE}/certs"
OIDC_OP_AUTHORIZATION_ENDPOINT = f"{_KC_PUBLIC_BASE}/auth"
OIDC_OP_TOKEN_ENDPOINT = f"{_KC_BASE}/token"
OIDC_OP_USER_ENDPOINT = f"{_KC_BASE}/userinfo"
OIDC_OP_LOGOUT_ENDPOINT = f"{_KC_PUBLIC_BASE}/logout"
OIDC_CREATE_USER = True
OIDC_STORE_ACCESS_TOKEN = True
OIDC_STORE_ID_TOKEN = True
OIDC_VERIFY_SSL = env.bool('OIDC_VERIFY_SSL', default=True)

LOGIN_URL = '/oidc/authenticate/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[%(asctime)s] %(levelname)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'loggers': {
        'accounts': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'mozilla_django_oidc': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
