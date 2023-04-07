# Python Standard Library
import uuid

# Django
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, EmailValidator
from django.db.models import (
    CASCADE,
    CharField,
    ForeignKey,
    Model,
    OneToOneField,
    SET_NULL,
    UUIDField
)

# DJango JSON:API Framework
from django_jsonapi_framework.exceptions import (
    ModelAttributeNotAllowedError,
    ModelAttributeRequiredError,
    ModelRelationshipNotAllowedError
)
from django_jsonapi_framework.permissions import (
    HasAll,
    HasAny,
    HasOrganization,
    HasPermission,
    Profile
)
from django_jsonapi_framework.utils import (
    camel_case_to_snake_case,
    snake_case_to_camel_case
)

# Django Model Signals
from django_model_signals.transceiver import ModelSignalsTransceiver


class UUIDModel(Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class JSONAPIModel(Model):

    def clean_field(self, field_name, field, value):
        try:
            field.clean(value, self)
        except ValidationError as e:
            e.error_dict = {
                'field_name': e.error_list
            }
            raise e

    def from_jsonapi_resource(self, resource, profile):
        for attribute_name, attribute_value in resource['attributes'].items():
            attribute_name = camel_case_to_snake_case(attribute_name)
            if attribute_name not in profile.attributes:
                raise ModelAttributeNotAllowedError({
                    'key': attribute_name
                })
            setattr(self, attribute_name, attribute_value)

        for relationship_name, relationship_value \
                in resource['relationships'].items():
            relationship_name = camel_case_to_snake_case(relationship_name)
            if relationship_name not in profile.relationships:
                raise ModelRelationshipNotAllowedError({
                    'key': relationship_name
                })
            if relationship_value['data'] is None:
                setattr(self, relationship_name, None)
            else:
                relationship_class = self._meta.get_field(relationship_name).related_model
                relationship_instance = relationship_class.objects.get(
                    id=relationship_value['data']['id'])
                setattr(self, relationship_name, relationship_instance)

    def to_jsonapi_resource(self, profile):
        attributes = {}
        for attribute_name in profile.attributes:
            attributes[snake_case_to_camel_case(attribute_name)] = getattr(
                self, attribute_name)

        relationships = {}
        for relationship_name in profile.relationships:
            relationship_value = getattr(self, relationship_name)
            if relationship_value is None:
                relationship_data = None
            else:
                relationship_data = {
                    'type': relationship_value.__class__.__name__,
                    'id': relationship_value.id
                }
            relationships[snake_case_to_camel_case(relationship_name)] = {
                'data': relationship_data
            }

        resource = {
            'id': self.id,
            'type': self.__class__.__name__,
        }
        if len(attributes.keys()) > 0:
            resource['attributes'] = attributes
        if len(relationships.keys()) > 0:
            resource['relationships'] = relationships

        return resource

    class JSONAPIMeta:
        resource_name = None
        create = None
        read = None
        update = None
        delete = None

    class Meta:
        abstract = True


class Organization(ModelSignalsTransceiver, JSONAPIModel, UUIDModel):
    name = CharField(
        blank=False,
        null=False,
        default=None,
        max_length=64
    )
    owner = OneToOneField(
        to='django_jsonapi_framework.User',
        on_delete=SET_NULL,
        blank=True,
        null=True,
        default=None,
        related_name='+'
    )

    class Meta:
        db_table = 'django_jsonapi_framework__organizations'

    class JSONAPIMeta:
        resource_name = 'organizations'
        create = Profile(
            condition=HasPermission('django_jsonapi_framework.organizations.create'),
            attributes=['name']
        )
        read = Profile(
            condition=HasAny(
                HasPermission('django_jsonapi_framework.organizations.read_all'),
                HasAll(
                    HasOrganization('id'),
                    HasPermission('django_jsonapi_framework.organizations.read_own')
                )
            ),
            attributes=['name'],
            relationships=['owner']
        )
        update = Profile(
            condition=HasAny(
                HasPermission('django_jsonapi_framework.organizations.update_all'),
                HasAll(
                    HasOrganization('id'),
                    HasPermission('django_jsonapi_framework.organizations.update_own')
                )
            ),
            attributes=['name']
        )
        delete = Profile(
            condition=HasAny(
                HasPermission('django_jsonapi_framework.organizations.delete_all'),
                HasAll(
                    HasOrganization('id'),
                    HasPermission('django_jsonapi_framework.organizations.delete_own')
                )
            )
        )


class User(ModelSignalsTransceiver, JSONAPIModel, UUIDModel):

    password = None

    email = CharField(
        blank=False,
        null=False,
        default=None,
        max_length=254,
        validators=[
            EmailValidator(allowlist=[])
        ]
    )
    password_hash = CharField(
        blank=False,
        null=False,
        default=None,
        max_length=254
    )
    organization = ForeignKey(
        to=Organization,
        on_delete=CASCADE,
        blank=False,
        null=False,
        default=None
    )

    def pre_full_clean(self, **kwargs):

        # Make sure there is a password or a password hash
        if self.password is None and self.password_hash is None:
            raise ModelAttributeRequiredError({
                'key': 'password'
            })

        # If there is a password, manually validate it, since it's not an
        # actual persisted field
        if self.password is not None:
            password_field = CharField(
                blank=False,
                null=False,
                default=None,
                max_length=128,
                validators=[
                    MinLengthValidator(8)
                ]
            )
            self.clean_field('password', password_field, self.password)

            # If the password is valid, create a password hash
            self.password_hash = make_password(self.password)

    class Meta:
        db_table = 'django_jsonapi_framework__users'

    class JSONAPIMeta:
        resource_name = 'users'
        create = Profile(
            condition=HasPermission('django_jsonapi_framework.organizations.create'),
            attributes=['email', 'password'],
            relationships=['organization']
        )
        read = Profile(
            condition=HasAny(
                HasPermission('django_jsonapi_framework.organizations.read_all'),
                HasAll(
                    HasOrganization('id'),
                    HasPermission('django_jsonapi_framework.organizations.read_own')
                )
            ),
            attributes=['email'],
            relationships=['organization']
        )
        update = Profile(
            condition=HasAny(
                HasPermission('django_jsonapi_framework.organizations.update_all'),
                HasAll(
                    HasOrganization('id'),
                    HasPermission('django_jsonapi_framework.organizations.update_own')
                )
            ),
            attributes=['email'],
            relationships=['organization']
        )
        delete = Profile(
            condition=HasAny(
                HasPermission('django_jsonapi_framework.organizations.delete_all'),
                HasAll(
                    HasOrganization('id'),
                    HasPermission('django_jsonapi_framework.organizations.delete_own')
                )
            )
        )

    class ModelSignalsMeta:
        signals = ['pre_full_clean']
