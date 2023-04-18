# Python Standard Library
import datetime
import secrets
import uuid

# Django
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import MinLengthValidator
from django.db.models import (
    AutoField,
    BooleanField,
    CASCADE,
    CharField,
    DateTimeField,
    DO_NOTHING,
    EmailField,
    ForeignKey,
    Model,
    PROTECT,
    SET_NULL,
    UUIDField
)
from django.db.utils import IntegrityError

# Django JSON:API Framework
from django_jsonapi_framework.exceptions import (
    ModelAttributeInvalidError,
    ModelAttributeRequiredError,
    ModelNotFoundError,
    NoContentError
)
from django_jsonapi_framework.utils import clean_field
from django_jsonapi_framework.auth.utils import get_auth_email_backend

# Django Model Signals
from django_model_signals.models import (
    PreFullCleanSignalMixin,
    PostFullCleanSignalMixin,
    PostFullCleanErrorSignalMixin,
    PostSaveErrorSignalMixin
)


class UUIDModel(Model):
    id = UUIDField(
        blank=False,
        null=False,
        default=uuid.uuid4,
        primary_key=True,
        editable=False
    )

    class Meta:
        abstract = True


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
    owner = ForeignKey(
        to='django_jsonapi_framework_auth.User',
        on_delete=PROTECT,
        blank=False,
        null=False,
        default=None
    )

    email = None
    raw_password = None

    def pre_full_clean(self, **kwargs):
        if self.owner_id is None:
            self.owner = User()
            self.owner.email = self.email
            self.owner.raw_password = self.raw_password
            self.owner.full_clean()
            self.owner.save()

    def post_full_clean_error(self, **kwargs):
        field_name = next(iter(kwargs['error'].error_dict))
        field_error = kwargs['error'].error_dict[field_name][0]
        if field_name == 'email' and field_error.code == 'unique':
            existing_user = User.objects.get(email=self.owner.email)
            auth_email_backend = get_auth_email_backend()
            auth_email_backend.send_create_organization_owner_email_already_exists_email(
                organization=self,
                user=existing_user
            )
        raise NoContentError()

    def post_save(self, **kwargs):
        auth_email_backend = get_auth_email_backend()
        auth_email_backend.send_create_organization_owner_email_confirmation_email(
            organization=self,
            user=self.owner
        )

    class Meta:
        db_table = 'django_jsonapi_framework_auth_organization'

    class ModelSignalsMeta:
        signals = [
            'pre_full_clean',
            'post_full_clean_error',
            'post_save'
        ]


class User(
    PreFullCleanSignalMixin,
    # PostFullCleanErrorSignalMixin,
    # PostSaveErrorSignalMixin,
    UUIDModel
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
                field_name='password',
                field=raw_password_field,
                value=self.raw_password
            )
            self.password = make_password(self.raw_password)
    #
    # def post_full_clean_error(self, **kwargs):
    #
    #     # When creating a new user...
    #     if kwargs['created']:
    #
    #         # ...if validating the user while creating caused a email not
    #         # unique error.
    #         field_name = next(iter(kwargs['error'].error_dict))
    #         field_error = kwargs['error'].error_dict[field_name][0]
    #         if field_name == 'email' and field_error.code == 'unique':
    #
    #             # ...send an email already exists email, prevent the user from
    #             # being persisted and return an empty response.
    #             # other_user = User.objects.filter(
    #             #     email=self.email
    #             # ).exclude(id=self.id).first()
    #             # auth_email_backend = get_auth_email_backend()
    #             # auth_email_backend.send_user_email_already_exists_email(
    #             #     user=other_user,
    #             #     created=True
    #             # )
    #             raise NoContentError()
    #
    #     raise kwargs['error']

    # def post_save(self, **kwargs):
    #
    #     # When creating a new user...
    #     if kwargs['created']:
    #
    #         # ...create a user email confirmation.
    #         user_email_confirmation = UserEmailConfirmation()
    #         user_email_confirmation.email = self.email
    #         user_email_confirmation.user = self
    #         user_email_confirmation.full_clean()
    #         user_email_confirmation.save()
    #
    # def post_save_error(self, **kwargs):
    #
    #     # When creating a new user...
    #     if kwargs['created']:
    #
    #         # ...if persisting the user caused a username (email) not unique
    #         # error, send an email already exists email and return an empty
    #         # response.
    #         if isinstance(kwargs['error'], IntegrityError) \
    #                 and kwargs['error'].args[0] == 1062 \
    #                 and 'django_jsonapi_framework_auth_user.email' in kwargs['error'].args[1]:
    #             # other_user = User.objects.filter(
    #             #     email=self.email
    #             # ).exclude(id=self.id).first()
    #             # auth_email_backend = get_auth_email_backend()
    #             # auth_email_backend.send_user_email_already_exists_email(
    #             #     user=other_user,
    #             #     created=True
    #             # )
    #             raise NoContentError()
    #
    #     raise kwargs['error']

    class Meta:
        db_table = 'django_jsonapi_framework_auth_user'

    class ModelSignalsMeta:
        signals = [
            'pre_full_clean',
            # 'post_full_clean_error',
            # 'post_save',
            # 'post_save_error'
        ]


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

    # def pre_full_clean(self, **kwargs):
    #
    #     # When creating a new user email confirmation...
    #     if kwargs['created']:
    #
    #         # ...generate a random token and store a hash of it,
    #         self.raw_token = secrets.token_urlsafe(128)
    #         self.token = make_password(self.raw_token)
    #
    #         # ...and set the expired_at to 15 minutes in the future.
    #         self.expired_at = \
    #             datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    #
    #     # Otherwise, when updating the user email confirmation...
    #     else:
    #
    #         # ...if the user email confirmation is expired, delete it and raise
    #         # a model not found error.
    #         if self.expired_at < datetime.datetime.utcnow():
    #             self.delete()
    #             raise ModelNotFoundError()
    #
    #         # ...if a token has not been provided, raise a token required
    #         # error.
    #         if not hasattr(self, 'raw_token'):
    #             raise ModelAttributeRequiredError({
    #                 'field': 'token'
    #             })
    #
    #         # ...or if the token is invalid, delete the user email and raise a
    #         # token invalid error.
    #         if not check_password(self.raw_token, self.token):
    #             self.delete()
    #             raise ModelAttributeInvalidError({
    #                 'field': 'token'
    #             })

    # def post_full_clean(self, **kwargs):
    #
    #     # When creating a new user email confirmation...
    #     if kwargs['created']:
    #
    #         # ...make sure the email is not already the confirmed email of the
    #         # current user.
    #         if self.email == self.user.email and self.user.is_email_confirmed:
    #             raise ModelAttributeInvalidError({
    #                 'field': 'email'
    #             })
    #
    #         # ...and if the email already belongs to another user, send an
    #         # email already exists email
    #         other_user = User.objects.filter(
    #             email=self.email
    #         ).exclude(id=self.user.id).first()
    #         if other_user is not None:
    #             auth_email_backend = get_auth_email_backend()
    #             auth_email_backend.send_user_email_already_exists_email(
    #                 user=other_user,
    #                 created=not user.is_email_confirmed
    #             )
    #             raise NoContentError()
    #
    # def post_save(self, **kwargs):
    #
    #     # When creating a new user email confirmation...
    #     if kwargs['created']:
    #
    #         # ...send an email confirmation email.
    #         auth_email_backend = get_auth_email_backend()
    #         auth_email_backend.send_user_email_confirmation_email(
    #             user_email_confirmation=self
    #         )
    #
    #     # Otherwise, when updating the user email...
    #     else:
    #
    #         # ...the email has been confirmed, so update the user,
    #         old_email = self.user.email
    #         self.user.email = self.email
    #         self.user.is_email_confirmed = True
    #         self.user.full_clean()
    #         self.user.save()
    #
    #         # ...and if the user's email address has changed, also send a
    #         # user email removed email.
    #         if old_email != self.email:
    #             auth_email_backend = get_auth_email_backend()
    #             auth_email_backend.send_update_user_email_removed_email(
    #                 user=self.user,
    #                 old_email=old_email
    #             )
    #
    #         # ...and delete the user email confirmation.
    #         self.delete()

    class Meta:
        db_table = 'django_jsonapi_framework_auth_users_email_confirmation'

    # class ModelSignalsMeta:
    #     signals = [
    #         'pre_full_clean',
    #         'post_full_clean',
    #         'post_save'
    #     ]


class UserPasswordChange(Model):
    id = AutoField(primary_key=True)
    current_password = CharField(
        blank=False,
        null=False,
        default=None,
        max_length=128,
        validators=[
            MinLengthValidator(8)
        ]
    )
    new_password = CharField(
        blank=False,
        null=False,
        default=None,
        max_length=128,
        validators=[
            MinLengthValidator(8)
        ]
    )
    user = ForeignKey(
        to=User,
        on_delete=DO_NOTHING,
        blank=False,
        null=False,
        default=None,
        related_name='+'
    )

    def save(self):

        # If the supplied current password matches the user's current password,
        # update the user's password. The UserPasswordChange model itself is
        # not persisted.
        if not check_password(self.current_password, self.user.password):
            raise ModelAttributeInvalidError({
                'field': 'current_password'
            })
        self.user.password = make_password(self.new_password)
        self.user.full_clean()
        self.user.save()

    class Meta:
        managed = False
