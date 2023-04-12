from django_jsonapi_framework.conf import settings


def get_auth_email_handler():
    return get_class_by_fully_qualified_name(settings['AUTH_EMAIL_HANDLER'])
