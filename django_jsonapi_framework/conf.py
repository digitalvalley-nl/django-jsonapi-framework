# Python Standard Library
from importlib import import_module

# Django
from django.conf import settings as django_settings


"""
Define the Django JSON:API Framework default settings.
"""
DEFAULTS = {}


"""
Define the Django JSON:API Framework settings object.
"""
settings = {}

"""
Load the user provided Django JSON:API Framework settings if provided.
"""
if hasattr(django_settings, 'DJANGO_JSONAPI_FRAMEWORK'):
    settings = django_settings.DJANGO_JSONAPI_FRAMEWORK


"""
Load the defaults for any Django JSON:API Framework setting the user has not
provided.
"""
for key, value in DEFAULTS.items():
    if key not in settings:
        settings[key] = value


"""
Load the defaults for any Django JSON:API Framework sub module setting the user
has not provided.
"""
for installed_app in django_settings.INSTALLED_APPS:
    if installed_app.startswith('django_jsonapi_framework.'):
        module_key = installed_app.replace(
            'django_jsonapi_framework.', '', 1).upper()
        MODULE_DEFAULTS = import_module(installed_app + '.conf').DEFAULTS
        if module_key not in settings:
            settings[module_key] = {}
        for key, value in MODULE_DEFAULTS.items():
            if key not in settings[module_key]:
                settings[module_key][key] = value
