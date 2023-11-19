# Python Standard Library
import datetime
import secrets

# Django
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db.models import (
    BooleanField,
    CASCADE,
    CharField,
    DateTimeField,
    DO_NOTHING,
    EmailField,
    ForeignKey,
    Model,
    OneToOneField,
    PROTECT,
    SET_NULL,
)
from django.db.utils import IntegrityError

# Django JSON:API Framework - Core
from django_jsonapi_framework.exceptions import (
    ModelError,
    ModelAttributeInvalidError,
    ModelAttributeRequiredError,
    ModelNotFoundError,
    NoContentError
)
from django_jsonapi_framework.models import UUIDModel
from django_jsonapi_framework.utils import clean_field

# Django JSON:API Framework - Auth
from django_jsonapi_framework.auth.utils import get_auth_email_backend

# Django Model Signals
from django_model_signals.models import (
    PreFullCleanSignalMixin,
    PostFullCleanSignalMixin,
    PostFullCleanErrorSignalMixin,
    PostSaveErrorSignalMixin
)


"""Model class that represents an organization."""
class Organization(
    PostFullCleanErrorSignalMixin,
    PreFullCleanSignalMixin,
    UUIDModel
):
    name = CharField(
        blank=False,
        null=False,
        default=None,
        max_length=64
    )
    owner = OneToOneField(
        to='django_jsonapi_framework_auth.User',
        on_delete=PROTECT,
        blank=True,
        null=True,
        default=None,
        related_name='owner_organization'
    )

    owner_email = None
    owner_raw_password = None

    def post_save(self, **kwargs):
        """If the organization was just created, also create the owner user.

        If creating the owner user fails, delete the organization. If the
        reason for the failure was that the owner email address already exists,
        return an empty response (for privacy reasons) and notify the owner
        via a notification email that their email address is already
        registered.

        If creating the user was successful, also return an empty response (for
        privacy reasons) and notify the owner via a notification email that
        they need to confirm their email address.
        """
        if kwargs['created']:
            auth_email_backend = get_auth_email_backend()
            try:
                owner = User()
                owner.email = self.owner_email
                owner.raw_password = self.owner_raw_password
                owner.organization = self
                owner.full_clean()
                owner.save()
                self.owner = owner
                self.save()
            except ModelError as error:
                self.delete()
                error.meta['key'] = 'owner_' + error.meta['key']
                raise error
            except ValidationError as error:
                self.delete()
                if 'email' in error.error_dict and error.error_dict['email'][0].code == 'unique':
                    auth_email_backend.send_organization_owner_email_already_exists(
                        organization=self,
                        owner=owner
                    )
                    raise NoContentError()
                error_dict = {}
                for key, value in error.error_dict.items():
                    error_dict['owner_' + key] = value
                raise ValidationError(error_dict)
            except Exception as error:
                self.delete()
                raise error
            owner_email_confirmation = UserEmailConfirmation()
            owner_email_confirmation.email = owner.email
            owner_email_confirmation.user = owner
            owner_email_confirmation.full_clean()
            owner_email_confirmation.save()
            auth_email_backend.send_organization_owner_email_confirmation(
                organization=self,
                owner=owner,
                owner_email_confirmation=owner_email_confirmation
            )

    class Meta:
        db_table = 'django_jsonapi_framework__auth__organization'

    class ModelSignalsMeta:
        signals = ['post_save']


"""Abstract model class that represents a model that belongs to an
organization.
"""
class OrganizationModel(UUIDModel):
    organization = ForeignKey(
        to=Organization,
        on_delete=PROTECT,
        blank=False,
        null=False,
        default=None
    )

    class Meta:
        abstract = True


"""Model class that represents a user."""
class User(
    PreFullCleanSignalMixin,
    OrganizationModel
):
    email = EmailField(
        blank=False,
        null=False,
        default=None,
        unique=True
    )
    is_email_confirmed = BooleanField(
        blank=False,
        null=False,
        default=False
    )
    password = CharField(
        blank=False,
        null=False,
        default=None,
        max_length=128
    )

    raw_password = None

    def pre_full_clean(self, **kwargs):
        """When creating a user, a raw password should be provided. The raw
        password is validated here and then hashed into a password hash which
        is stored in the user."""

        # Make sure there is a new password or a password
        if self.raw_password is None and self.password is None:
            raise ModelAttributeRequiredError({
                'key': 'password'
            })

        # If there is a new password, manually validate it and set it as the
        # password
        if hasattr(self, 'raw_password'):
            raw_password_field = CharField(
                blank=False,
                null=False,
                default=None,
                max_length=128,
                validators=[
                    MinLengthValidator(8)
                ]
            )
            clean_field(
                model=self,
                field=raw_password_field,
                value=self.raw_password
            )
            self.password = make_password(self.raw_password)

    class Meta:
        db_table = 'django_jsonapi_framework__auth__user'

    class ModelSignalsMeta:
        signals = ['pre_full_clean']

""""""
class UserEmailConfirmation(
    PreFullCleanSignalMixin,
    PostFullCleanSignalMixin,
    UUIDModel
):
    email = EmailField(
        blank=False,
        null=False,
        default=None,
        editable=False
    )
    token = CharField(
        blank=False,
        null=False,
        default=None,
        max_length=128,
        editable=False
    )
    expired_at = DateTimeField(
        blank=False,
        null=False,
        default=None,
        editable=False
    )
    user = ForeignKey(
        to=User,
        on_delete=CASCADE,
        blank=False,
        null=False,
        default=None,
        related_name='+',
        editable=False
    )

    raw_token = None

    def pre_full_clean(self, **kwargs):

        # When creating a new user email confirmation...
        if kwargs['created']:

            # ...generate a random token and store a hash of it,
            self.raw_token = secrets.token_urlsafe(128)
            self.token = make_password(self.raw_token)

            # ...and set the expired_at to 15 minutes in the future.
            self.expired_at = \
                datetime.datetime.utcnow() + datetime.timedelta(minutes=15)

    def post_save(self, **kwargs):
        """If the user email confirmation was just updated, make sure the
        provided token is valid, mark the user's email address as confirmed,
        and delete the email address confirmation.
        """

        # When updating a user email confirmation...
        if not kwargs['created']:

            # ...if the user email confirmation is expired, delete it and raise
            # a model not found error.
            if self.expired_at < datetime.datetime.utcnow():
                self.delete()
                raise ModelNotFoundError()

            # ...if a token has not been provided, delete it and raise a token
            # required error.
            if self.raw_token is None:
                self.delete()
                raise ModelAttributeRequiredError({
                    'field': 'token'
                })

            # ...or if the token is invalid, delete the user email confirmation
            # and raise a token invalid error.
            if not check_password(self.raw_token, self.token):
                self.delete()
                raise ModelAttributeInvalidError({
                    'field': 'token'
                })

            # If all above checks have passed, mark the user's email address as
            # confirmed and delete the user email confirmation.
            self.user.is_email_confirmed = True
            self.user.save()
            self.delete()

    class Meta:
        db_table = 'django_jsonapi_framework__auth__user_email_confirmation'

    class ModelSignalsMeta:
        signals = ['pre_full_clean', 'post_save']
