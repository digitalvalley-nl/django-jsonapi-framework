# Python Standard Library
import uuid

# Django
from django.db.models import Model, UUIDField

# DJango JSON:API Framework
from django_jsonapi_framework.exceptions import (
    ModelAttributeNotAllowedError,
    ModelAttributeRequiredError,
    ModelRelationshipNotAllowedError
)
from django_jsonapi_framework.utils import (
    camel_case_to_snake_case,
    snake_case_to_camel_case
)


class JSONAPIBaseModel(Model):
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
            if attribute_name in profile.attribute_mappings:
                attribute_name = profile.attribute_mappings[attribute_name]
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
                relationship_class = \
                    self._meta.get_field(relationship_name).related_model
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

        id_field = 'id'
        if hasattr(self.JSONAPIMeta, 'id_field'):
            id_field = self.JSONAPIMeta.id_field
        resource = {
            'id': getattr(self, id_field),
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


class JSONAPIModel(JSONAPIBaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True
