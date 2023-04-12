# Python Standard Library
import copy
import json
from pathlib import Path

# Django
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.http import HttpResponse, JsonResponse
from django.urls import path
from django.db.models.fields import Field

# Django JSON:API Framework
from django_jsonapi_framework.exceptions import (
    ModelAttributeNotAllowedError,
    ModelAttributeRequiredError,
    ModelAttributeTooLongError,
    ModelAttributeTooShortError,
    ModelRelationshipNotAllowedError,
    ModelIdDoesNotMatchError,
    ModelNotFoundError,
    ModelTypeInvalidError,
    RequestBodyJsonDecodeError,
    RequestBodyJsonSchemaError,
    RequestHeaderInvalidError,
    RequestMethodNotAllowedError,
    VALIDATION_ERRORS
)
from django_jsonapi_framework.utils import (
    camel_case_to_snake_case,
    get_class_by_fully_qualified_name,
    snake_case_to_camel_case
)

# JSON Schema
import jsonschema


class JSONAPIModelResource:
    basename = None
    model = None
    id_field = 'id'
    create_profile = None
    read_profile = None
    update_profile = None
    delete_profile = None

    __schemas = {}
    with open(str(Path(__file__).resolve().parent) + '/schema.json') as file:
        __schemas['update'] = json.loads(file.read())
    __schemas['create'] = copy.deepcopy(__schemas['update'])
    __schemas['create']['definitions']['resource']['required'].remove('id')
    del __schemas['create']['definitions']['resource']['properties']['id']

    @classmethod
    def get_urlpatterns(cls):
        return [
            path(cls.basename + '/', cls.dispatch),
            path(cls.basename + '/<id>/', cls.dispatch)
        ]

    @classmethod
    def __create(cls, request):

        # Parse the request
        cls.__validate_request_headers(request)
        data = cls.__parse_request_body(request, 'create')
        model_data = cls.__parse_model_data(data['data'])
        print(model_data['type'])
        print(cls.model.__name__)
        if model_data['type'] != cls.model.__name__:
            raise ModelTypeInvalidError()

        # Create the model
        model = cls.model()
        create_profile = cls.create_profile.resolve(None)
        cls.populate_model_from_resource(model, model_data, create_profile)
        is_valid = cls.__validate_model(model)
        if is_valid != False:
            model.save()

        # Return the model data
        if create_profile.show_response:
            read_profile = cls.read_profile.resolve(None)
            return JsonResponse({
                'data': cls.render_model_to_resource(model, read_profile)
            })
        else:
            return HttpResponse(status=204)

    @classmethod
    def __delete(cls, request, id):
        model = cls.__get_model(id)
        model.delete()
        return HttpResponse(status=204)

    @classmethod
    def dispatch(cls, request, id=None):
        if request.method == 'GET':
            if id is None:
                return cls.__list(request)
            return cls.__get(request, id)
        if request.method == 'POST':
            return cls.__create(request)
        if request.method == 'PATCH':
            return cls.__update(request, id)
        if request.method == 'DELETE':
            return cls.__delete(request, id)
        raise RequestMethodNotAllowedError()

    @classmethod
    def __get(cls, request, id):
        model = cls.__get_model(id)
        read_profile = cls.read_profile.resolve(None)
        return JsonResponse({
            'data': cls.render_model_to_resource(model, read_profile)
        })

    @classmethod
    def __list(cls, request):
        models = cls.model.objects.all()
        read_profile = cls.read_profile.resolve(None)
        return JsonResponse({
            'data': list(
                map(
                    lambda model: cls.render_model_to_resource(model, read_profile),
                    models
                )
            )
        })

    @classmethod
    def __update(cls, request, id):

        # Parse the request
        cls.__validate_request_headers(request)
        data = cls.__parse_request_body(request, 'update')
        model_data = cls.__parse_model_data(data['data'])
        if model_data['type'] != cls.model.__name__:
            raise ModelTypeInvalidError()
        if model_data['id'] != id:
            raise ModelIdDoesNotMatchError()

        # Create the model
        model = cls.__get_model(id)
        update_profile = cls.update_profile.resolve(None)
        cls.populate_model_from_resource(model, model_data, update_profile)
        is_valid = cls.__validate_model(model)
        if is_valid != False:
            model.save()

        # Return the model data
        if update_profile.show_response:
            read_profile = cls.read_profile.resolve(None)
            return JsonResponse({
                'data': cls.render_model_to_resource(model, read_profile)
            })
        else:
            return HttpResponse(status=204)

    @classmethod
    def __get_model(cls, id):
        try:
            id_field = 'id'
            if hasattr(cls, 'id_field'):
                id_field = cls.id_field
            kwargs = {
                id_field: id
            }
            model = cls.model.objects.get(**kwargs)
        except cls.model.DoesNotExist:
            raise ModelNotFoundError()
        return model

    @classmethod
    def __validate_request_headers(cls, request):
        if request.headers['Content-Type'] != 'application/vnd.api+json':
            raise RequestHeaderInvalidError({
                'key': 'Content-Type',
                'value': request.headers['Content-Type']
            })

    @classmethod
    def __parse_request_body(cls, request, schema):
        # Parse the JSON:API data
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            raise RequestBodyJsonDecodeError() # TODO: Give more error details

        # Validate the JSON:API data
        try:
            jsonschema.validate(instance=data, schema=cls.__schemas[schema])
        except jsonschema.exceptions.ValidationError:
            raise RequestBodyJsonSchemaError() # TODO: Give more error details

        return data

    @classmethod
    def __parse_model_data(cls, model_data):
        if 'attributes' not in model_data:
            model_data['attributes'] = {}
        if 'relationships' not in model_data:
            model_data['relationships'] = {}
        return model_data

    @classmethod
    def __validate_model(cls, model):
        try:
            return model.full_clean()
        except ValidationError as error:

            # Get the field name and error
            field_name = next(iter(error.error_dict))
            field_error = error.error_dict[field_name][0]

            # Convert the error to a bad request error if recognized
            if field_error.code in VALIDATION_ERRORS:
                meta = {
                    'field': field_name
                }
                if field_error.code == 'blank':
                    meta['min_length'] = 1
                    for validator in model._meta.get_field(field_name).validators:
                        if isinstance(validator, MinLengthValidator):
                            meta['min_length'] = validator.limit_value
                elif field_error.code == 'min_length':
                    meta['min_length'] = field_error.params['limit_value']
                elif field_error.code == 'max_length':
                    meta['max_length'] = field_error.params['limit_value']
                elif field_error.code == 'unique_together':
                    del meta['field']
                    meta['fields'] = field_error.params['unique_check']
                error = VALIDATION_ERRORS[field_error.code](meta=meta)

            raise error


    @classmethod
    def populate_model_from_resource(cls, model, resource, profile):
        for attribute_name, attribute_value in resource['attributes'].items():
            attribute_name = camel_case_to_snake_case(attribute_name)
            if attribute_name not in profile.attributes:
                raise ModelAttributeNotAllowedError({
                    'key': attribute_name
                })
            if attribute_name in profile.attribute_mappings:
                attribute_name = profile.attribute_mappings[attribute_name]
            setattr(model, attribute_name, attribute_value)

        for relationship_name, relationship_value \
                in resource['relationships'].items():
            relationship_name = camel_case_to_snake_case(relationship_name)
            if relationship_name not in profile.relationships:
                raise ModelRelationshipNotAllowedError({
                    'key': relationship_name
                })
            if relationship_value['data'] is None:
                setattr(model, relationship_name, None)
            else:
                resource_class = profile.relationships[relationship_name]
                if isinstance(resource_class, str):
                    resource_class = get_class_by_fully_qualified_name(
                        resource_class
                    )
                id_field = resource_class.id_field
                relationship_instance = resource_class.model.objects.get(**{
                    id_field: relationship_value['data']['id']
                })
                setattr(model, relationship_name, relationship_instance)

    @classmethod
    def render_model_to_resource(cls, model, profile):
        attributes = {}
        for attribute_name in profile.attributes:
            attributes[snake_case_to_camel_case(attribute_name)] = getattr(
                model, attribute_name)

        relationships = {}
        for relationship_name in profile.relationships:
            relationship_value = getattr(model, relationship_name)
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
            'id': getattr(model, cls.id_field),
            'type': model.__class__.__name__,
        }
        if len(attributes.keys()) > 0:
            resource['attributes'] = attributes
        if len(relationships.keys()) > 0:
            resource['relationships'] = relationships

        return resource
