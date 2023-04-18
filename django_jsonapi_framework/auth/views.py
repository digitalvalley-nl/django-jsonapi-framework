# Django JSON:API Framework
from django_jsonapi_framework.views import JSONAPIResource
from django_jsonapi_framework.auth.models import (
    Organization,
    User,
    UserEmailConfirmation,
    UserPasswordChange
)
from django_jsonapi_framework.auth.permissions import (
    AllOf,
    AnyOf,
    ModelFieldIsEqualToOwnField,
    UserHasGlobalPermission,
    UserHasPermissionInOrganizationOfModel,
    Profile
)


class OrganizationResource(JSONAPIResource):
    basename = 'organizations'
    model = Organization
    create_profile = Profile(
        attributes=['name', 'email', 'password'],
        attribute_mappings={
            'password': 'raw_password'
        },
        show_response=False
    )
    read_profile = Profile(
        condition=AnyOf(
            UserHasGlobalPermission(
                'django_jsonapi_framework_auth.organizations.read_all'
            ),
            UserHasPermissionInOrganizationOfModel(
                'django_jsonapi_framework_auth.organizations.read_own'
            )
        ),
        attributes=['name'],
        relationships={
            'owner': 'django_jsonapi_framework.auth.views.UserResource'
        }
    )
    update_profile = Profile(
        condition=AnyOf(
            UserHasGlobalPermission(
                'django_jsonapi_framework_auth.organizations.update_all'
            ),
            UserHasPermissionInOrganizationOfModel(
                'django_jsonapi_framework_auth.organizations.update_own'
            )
        ),
        attributes=['name']
    )
    delete_profile = Profile(
        condition=AnyOf(
            UserHasGlobalPermission(
                'django_jsonapi_framework_auth.organizations.delete_all'
            ),
            UserHasPermissionInOrganizationOfModel(
                'django_jsonapi_framework_auth.organizations.delete_own'
            )
        )
    )


class UserResource(JSONAPIResource):
    basename = 'users'
    model = User
    create_profile = Profile(
        condition=AnyOf(
            UserHasGlobalPermission(
                'django_jsonapi_framework_auth.users.create_all'
            ),
            AllOf(
                ModelFieldIsEqualToOwnField('id', 'id'),
                UserHasGlobalPermission(
                    'django_jsonapi_framework_auth.users.create_own'
                )
            )
        ),
        attributes=['email', 'password'],
        attribute_mappings={
            'password': 'raw_password'
        },
        relationships={
            'organization': OrganizationResource
        },
        show_response=False
    )
    read_profile = Profile(
        condition=AnyOf(
            UserHasGlobalPermission(
                'django_jsonapi_framework_auth.users.read_all'
            ),
            UserHasPermissionInOrganizationOfModel(
                'django_jsonapi_framework_auth.users.read_own'
            ),
            AllOf(
                ModelFieldIsEqualToOwnField('id', 'id'),
                UserHasPermissionInOrganizationOfModel(
                    'django_jsonapi_framework_auth.users.read_self'
                )
            )

        ),
        attributes=['email', 'is_email_confirmed'],
        relationships={
            'organization': OrganizationResource
        }
    )
    delete_profile = Profile(
        condition=AnyOf(
            UserHasGlobalPermission(
                'django_jsonapi_framework_auth.users.delete_all'
            ),
            UserHasPermissionInOrganizationOfModel(
                'django_jsonapi_framework_auth.users.delete_own'
            ),
            AllOf(
                ModelFieldIsEqualToOwnField('id', 'id'),
                UserHasPermissionInOrganizationOfModel(
                    'django_jsonapi_framework_auth.users.delete_self'
                )
            )
        )
    )

class UserEmailConfirmationResource(JSONAPIResource):
    basename = 'users/email-confirmation'
    model = UserEmailConfirmation

    create_profile = Profile(
        relationships={
            'user': UserResource
        },
        show_response=False
    )
    update_profile = Profile(
        attributes=['token'],
        attribute_mappings={
            'token': 'raw_token'
        },
        show_response=False
    )


class UserPasswordChangeResource(JSONAPIResource):
    basename = 'users/password-change'
    model = UserPasswordChange
    create_profile = Profile(
        condition=AllOf(
            ModelFieldIsEqualToOwnField('user_id', 'id'),
            UserHasPermissionInOrganizationOfModel(
                'django_jsonapi_framework_auth.user_passwords.create_self'
            )
        ),
        attributes=['current_password', 'new_password'],
        relationships={
            'user': UserResource
        },
        show_response=False
    )
