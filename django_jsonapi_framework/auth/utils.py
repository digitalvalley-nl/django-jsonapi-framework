# Django JSON:API Framework
from django_jsonapi_framework.conf import settings
from django_jsonapi_framework.utils import get_class_by_fully_qualified_name


def get_auth_email_backend():
    return get_class_by_fully_qualified_name(settings['AUTH_EMAIL_BACKEND'])
