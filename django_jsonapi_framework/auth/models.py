# Python Standard Library
import uuid

# Django
from django.contrib.auth.models import User as DjangoUser
from django.core.validators import MinLengthValidator
from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    ForeignKey,
    Model,
    SET_NULL,
    UUIDField
)
from django.db.utils import IntegrityError

# Django JSON:API Framework
from django_jsonapi_framework.exceptions import ModelAttributeRequiredError
from django_jsonapi_framework.utils import (
    get_class_by_fully_qualified_name,
    clean_field
)
from django_jsonapi_framework.auth.utils import get_auth_email_handler

# Django Model Signals
from django_model_signals.transceiver import ModelSignalsTransceiver


class Organization(Model):
    id = UUIDField(
        blank=False,
        null=False,
        default=uuid.uuid4,
        primary_key=True,
        editable=False
    )
    name = CharField(
        blank=False,
        null=False,
        default=None,
        max_length=64
    )
    owner = ForeignKey(
        to='django_jsonapi_framework__auth.User',
        on_delete=SET_NULL,
        blank=True,
        null=True,
        default=None,
        related_name='+'
    )

    class Meta:
        db_table = 'django_jsonapi_framework__auth__organizations'


class User(ModelSignalsTransceiver, DjangoUser):
    uuid = UUIDField(
        blank=False,
        null=False,
        default=uuid.uuid4,
        editable=False
    )
    organization = ForeignKey(
        to=Organization,
        on_delete=CASCADE,
        blank=False,
        null=False,
        default=None,
        related_name='+'
    )
    is_email_confirmed = BooleanField(
        blank=False,
        null=False,
        default=False
    )

    def pre_full_clean(self, **kwargs):

        # Make sure the username is always equal to the email
        self.username = self.email

        # Make sure there is a new password or a password
        if not hasattr(self, 'raw_password') and len(self.password) == 0:
            raise ModelAttributeRequiredError({
                'key': 'password'
            })

        # If there is a new password, manually validate it and set it as the
        # password
        if hasattr(self, 'raw_password') is not None:
            raw_password_field = CharField(
                blank=False,
                null=False,
                default=None,
                max_length=128,
                validators=[
                    MinLengthValidator(8)
                ]
            )
            clean_field('password', raw_password_field, self.raw_password)
            self.set_password(self.raw_password)

    def post_full_clean_error(self, **kwargs):

        # If validating the user while creating caused a username (email) not
        # unique error, send an email to the user to notify them that they
        # already have an account, suppress the error and stop the model from
        # being persisted.
        if kwargs['created']:
            field_name = next(iter(kwargs['error'].error_dict))
            field_error = kwargs['error'].error_dict[field_name][0]
            if field_name == 'username' and field_error.code == 'unique':
                auth_email_handler = get_auth_email_handler()
                auth_email_handler.send_email_already_exists_email(self)
                return False

        raise error

    def post_save(self, **kwargs):

        # If the user was successfully created, send an email confirmation
        # email.
        if kwargs['created']:
            auth_email_handler = get_auth_email_handler()
            auth_email_handler.send_email_confirmation_email(self)

    def post_save_error(self, error, created):

        # If creating the user caused a username (email) not unique error, send
        # an email to the user to notify them that they already have an account
        # and suppress the error.
        if isinstance(error, IntegrityError) \
                and error.args[0] == 1062 \
                and 'auth_user.username' in error.args[1]:
            auth_email_handler = get_auth_email_handler()
            auth_email_handler.send_email_already_exists_email(self)

    class Meta:
        db_table = 'django_jsonapi_framework__auth__users'

    class ModelSignalsMeta:
        signals = [
            'pre_full_clean',
            'post_full_clean_error',
            'post_save',
            'post_save_error'
        ]
