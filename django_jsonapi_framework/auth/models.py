# Python Standard Library
import uuid

# Django
from django.conf import settings
from django.contrib.auth.models import User as DjangoUser
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, EmailValidator
from django.db.models import (
    CASCADE,
    CharField,
    ForeignKey,
    Model,
    OneToOneField,
    SET_NULL,
    UniqueConstraint,
    UUIDField
)
from django.db.utils import IntegrityError

# Django JSON:API Framework
from django_jsonapi_framework.exceptions import ModelAttributeRequiredError
from django_jsonapi_framework.models import (
    JSONAPIBaseModel,
    JSONAPIModel
)
from django_jsonapi_framework.auth.permissions import (
    HasAll,
    HasAny,
    HasPermission,
    IsEqual,
    IsEqualToOwn,
    IsNone,
    IsNotNone,
    IsOwnOrganization,
    Profile,
    ProfileResolver
)
from django_jsonapi_framework.utils import get_class_by_fully_qualified_name

# Django Model Signals
from django_model_signals.transceiver import ModelSignalsTransceiver


class Organization(JSONAPIModel):
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

    class JSONAPIMeta:
        resource_name = 'organizations'
        create = Profile(
            condition=HasPermission(
                'django_jsonapi_framework__auth.organizations.create_all'
            ),
            attributes=['name']
        )
        read = Profile(
            condition=HasAny(
                HasPermission(
                    'django_jsonapi_framework__auth.organizations.read_all'
                ),
                HasAll(
                    IsOwnOrganization('id'),
                    HasPermission(
                        'django_jsonapi_framework__auth.organizations.read_own'
                    )
                )
            ),
            attributes=['name'],
            relationships=['owner']
        )
        update = Profile(
            condition=HasAny(
                HasPermission(
                    'django_jsonapi_framework__auth.organizations.update_all'
                ),
                HasAll(
                    IsOwnOrganization('id'),
                    HasPermission(
                        'django_jsonapi_framework__auth.organizations.update_own'
                    )
                )
            ),
            attributes=['name']
        )
        delete = Profile(
            condition=HasAny(
                HasPermission(
                    'django_jsonapi_framework__auth.organizations.delete_all'
                ),
                HasAll(
                    IsOwnOrganization('id'),
                    HasPermission(
                        'django_jsonapi_framework__auth.organizations.delete_own'
                    )
                )
            )
        )


class User(JSONAPIBaseModel, ModelSignalsTransceiver, DjangoUser):
    uuid = UUIDField(default=uuid.uuid4, editable=False)
    organization = ForeignKey(
        to=Organization,
        on_delete=CASCADE,
        blank=False,
        null=False,
        default=None,
        related_name='+'
    )

    new_password = None

    def pre_full_clean(self, **kwargs):

        # Make sure the username is always the email
        self.username = self.email

        # Make sure there is a new password or a password
        if self.new_password is None and len(self.password) == 0:
            raise ModelAttributeRequiredError({
                'key': 'password'
            })

        # If there is a new password, manually validate it and set it as the
        # password
        if self.new_password is not None:
            new_password_field = CharField(
                blank=False,
                null=False,
                default=None,
                max_length=128,
                validators=[
                    MinLengthValidator(8)
                ]
            )
            self.clean_field('password', new_password_field, self.new_password)
            self.set_password(self.new_password)

    def post_full_clean_error(self, error, created):
        field_name = next(iter(error.error_dict))
        field_error = error.error_dict[field_name][0]
        if field_name == 'username' and field_error.code == 'unique':
            auth_email_handler = get_class_by_fully_qualified_name(
                settings.DJANGO_JSONAPI_FRAMEWORK['AUTH_EMAIL_HANDLER']
            )
            auth_email_handler.send_email_already_exists_email(self)
            return False
        raise error

    def post_save(self, **kwargs):
        if kwargs['created']:
            auth_email_handler = get_class_by_fully_qualified_name(
                settings.DJANGO_JSONAPI_FRAMEWORK['AUTH_EMAIL_HANDLER']
            )
            auth_email_handler.send_email_confirmation_email(self)

    def post_save_error(self, error, created):
        if isinstance(error, IntegrityError) \
                and error.args[0] == 1062 \
                and 'auth_user.username' in error.args[1]:
            auth_email_handler = get_class_by_fully_qualified_name(
                settings.DJANGO_JSONAPI_FRAMEWORK['AUTH_EMAIL_HANDLER']
            )
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

    class JSONAPIMeta:
        resource_name = 'users'
        id_field = 'uuid'
        create = ProfileResolver(
            Profile(
                condition=HasPermission(
                    'django_jsonapi_framework__auth.users.create_all'
                ),
                attributes=['email', 'password'],
                attribute_mappings={
                    'password': 'new_password'
                },
                relationships=['organization'],
                show_response=False
            ),
            Profile(
                condition=HasPermission(
                    'django_jsonapi_framework__auth.users.create_own'
                ),
                attributes=['email', 'password'],
                attribute_mappings={
                    'password': 'new_password'
                },
                relationships=['organization'],
                show_response=False
            )
        )
        read = Profile(
            condition=HasAny(
                HasPermission(
                    'django_jsonapi_framework__auth.users.read_all'
                ),
                HasAll(
                    IsOwnOrganization(),
                    HasPermission(
                        'django_jsonapi_framework__auth.users.read_own'
                    )
                )
            ),
            attributes=['email']
        )
        update = ProfileResolver(
            Profile(
                condition=HasPermission(
                    'django_jsonapi_framework__auth.users.update_all'
                ),
                relationships=['organization']
            ),
            Profile(
                condition=HasAll(
                    IsOwnOrganization(),
                    HasPermission(
                        'django_jsonapi_framework__auth.users.update_own'
                    )
                )
                # TODO: Add fields an organization admin can edit
            ),
            Profile(
                condition=HasAll(
                    IsEqualToOwn('id', 'id'),
                    HasPermission(
                        'django_jsonapi_framework__auth.users.update_self'
                    )
                )
                # TODO: Add fields a regular user can edit
            )
        )
        delete = Profile(
            condition=HasAny(
                HasPermission(
                    'django_jsonapi_framework__auth.users.delete_all'
                ),
                HasAll(
                    IsOwnOrganization('id'),
                    HasPermission(
                        'django_jsonapi_framework__auth.users.delete_own'
                    )
                ),
                HasAll(
                    IsOwnOrganization('id'),
                    HasPermission(
                        'django_jsonapi_framework__auth.users.delete_self'
                    )
                )
            )
        )
