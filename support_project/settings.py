import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = '*q7y!no&i@i#oo3f2me@((^8gi1w=rl6igb2btsa5tv-g(ra+s'

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '127.0.0.1:8080']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'support_system',
    'report_system',
    'crispy_forms',
    'drf_yasg',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'support_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'support_system.views.notifications_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'support_project.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'support_system',
        'USER': 'root',
        'PASSWORD': '7878',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

AUTH_USER_MODEL = 'support_system.User'

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'vbhghgjfghkjhkg@gmail.com'
EMAIL_HOST_PASSWORD = 'vbhghgjfghkjhkg@gmail.com'
DEFAULT_FROM_EMAIL = 'Служба поддержки <vbhghgjfghkjhkg@gmail.com>'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8080",
    "https://127.0.0.1:8080",
]

SWAGGER_SETTINGS = {
    'DEFAULT_API_URL': 'http://127.0.0.1:8080/api/',
    'SECURITY_DEFINITIONS': {
        'APIKey': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'API Key Authorization header. Example: "Api-Key YOUR_API_KEY"'
        }
    },
    'USE_SESSION_AUTH': False,
    'USE_BASIC_AUTH': False,
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'support_system.authentication.APIKeyAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}