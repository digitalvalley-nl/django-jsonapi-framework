from django.conf import settings as django_settings


DEFAULTS = {
    'AUTH_EMAIL_BACKEND': None
}


settings = DEFAULTS


if hasattr(django_settings, 'DJANGO_JSONAPI_FRAMEWORK'):
    settings = django_settings.DJANGO_JSONAPI_FRAMEWORK
    for key, value in DEFAULTS.items():
        if key not in settings:
            settings[key] = value
