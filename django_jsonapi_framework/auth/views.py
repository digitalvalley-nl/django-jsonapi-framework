# Django JSON:API Framework
from django_jsonapi_framework.views import JSONAPIModelResource
from django_jsonapi_framework.auth.models import Organization, User
from django_jsonapi_framework.auth.permissions import (
    HasAll,
    HasAny,
    HasPermission,
    IsEqualToOwn,
    IsOwnOrganization,
    Profile
)


class OrganizationResource(JSONAPIModelResource):
    basename = 'organizations'
    model = Organization
    create_profile = Profile(
        condition=HasPermission(
            'django_jsonapi_framework__auth.organizations.create_all'
        ),
        attributes=['name']
    )
    read_profile = Profile(
        condition=HasAny(
            HasPermission(
                'django_jsonapi_framework__auth.organizations.read_all'
            ),
            HasAll(
                IsEqualToOwn('id', 'organization_id'),
                HasPermission(
                    'django_jsonapi_framework__auth.organizations.read_own'
                )
            )
        ),
        attributes=['name'],
        relationships=['owner']
    )
    update_profile = Profile(
        condition=HasAny(
            HasPermission(
                'django_jsonapi_framework__auth.organizations.update_all'
            ),
            HasAll(
                IsEqualToOwn('id', 'organization_id'),
                HasPermission(
                    'django_jsonapi_framework__auth.organizations.update_own'
                )
            )
        ),
        attributes=['name']
    )
    delete_profile = Profile(
        condition=HasAny(
            HasPermission(
                'django_jsonapi_framework__auth.organizations.delete_all'
            ),
            HasAll(
                IsEqualToOwn('id', 'organization_id'),
                HasPermission(
                    'django_jsonapi_framework__auth.organizations.delete_own'
                )
            )
        )
    )


class UserResource(JSONAPIModelResource):
    basename = 'users'
    model = User
    id_field = 'uuid'
    create_profile = Profile(
        condition=HasAny(
            HasPermission(
                'django_jsonapi_framework__auth.users.create_all'
            ),
            HasPermission(
                'django_jsonapi_framework__auth.users.create_own'
            )
        ),
        attributes=['email', 'password'],
        attribute_mappings={
            'password': 'raw_password'
        },
        relationships=['organization'],
        show_response=False
    )
    read_profile = Profile(
        condition=HasAny(
            HasPermission(
                'django_jsonapi_framework__auth.users.read_all'
            ),
            HasAll(
                IsOwnOrganization(),
                HasAny(
                    HasPermission(
                        'django_jsonapi_framework__auth.users.read_own'
                    ),
                    HasPermission(
                        'django_jsonapi_framework__auth.users.read_self'
                    )
                )
            )
        ),
        attributes=['email'],
        relationships=['organization']
    )
    delete_profile = Profile(
        condition=HasAny(
            HasPermission(
                'django_jsonapi_framework__auth.users.delete_all'
            ),
            HasAll(
                IsOwnOrganization(),
                HasAny(
                    HasPermission(
                        'django_jsonapi_framework__auth.users.delete_own'
                    ),
                    HasPermission(
                        'django_jsonapi_framework__auth.users.delete_self'
                    )
                )
            )
        )
    )
