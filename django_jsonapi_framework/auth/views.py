# Django JSON:API Framework - Core
from django_jsonapi_framework.views import (
    JSONAPIResource,
    JSONAPIResourceProfile
)

# Django JSON:API Framework - Auth
from django_jsonapi_framework.auth.models import (
    Organization,
    UserEmailConfirmation
)

"""Class used to configure the behaviour of the request methods of a
JSON:API resource in relation to the currently authenticated user.
"""
class AuthProfile(JSONAPIResourceProfile):
    def __init__(
        self,
        attributes=None,
        attribute_mappings=None,
        relationships=None,
        show_response=True,
        condition=None
    ):
        """Initialized the profile."""
        super().__init__(
            attributes=attributes,
            attribute_mappings=attribute_mappings,
            relationships=relationships,
            show_response=show_response
        )
        self.__condition = condition


"""Class used to configure an organization resource."""
class OrganizationResource(JSONAPIResource):
    basename = 'organizations'
    model = Organization
    create_profile = JSONAPIResourceProfile(
        attributes=['name', 'owner_email', 'owner_password'],
        attribute_mappings={
            'owner_password': 'owner_raw_password'
        },
        show_response=False
    )

"""Class used to configure a user email confirmation resource."""
class UserEmailConfirmationResource(JSONAPIResource):
    basename = 'users/email-confirmations'
    model = UserEmailConfirmation
    update_profile = JSONAPIResourceProfile(
        attributes=['token'],
        attribute_mappings={
            'token': 'raw_token'
        },
        show_response=False
    )
