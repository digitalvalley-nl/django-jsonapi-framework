# Python Standard Library
import json

# Django
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.http import JsonResponse
from django.urls import path
from django.db.models.fields import Field

# Django JSON:API Framework
from django_jsonapi_framework.exceptions import (
    ModelAttributeRequiredError,
    ModelAttributeTooLongError,
    ModelAttributeTooShortError,
    RequestBodyJsonDecodeError,
    RequestBodyJsonSchemaError,
    RequestMethodNotAllowedError,
    VALIDATION_ERRORS
)

# JSON Schema
import jsonschema


class ModelViewSet:
    actions = []
    basename = None
    model = None

    __create_schema = {
        'type': 'object',
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': 'https://django-jsonapi-framework.org/schemas/create.json',
        'properties': {
            'data': {
                'type': 'object',
                'properties': {
                    'type': {
                        'type': 'string'
                    },
                    'attributes': {
                        'type': 'object',
                        'patternProperties': {
                            '.*': {
                                'type': [
                                    'boolean',
                                    'integer',
                                    'number',
                                    'null',
                                    'string'
                                ]
                            }
                        },
                        'additionalProperties': False
                    },
                    'relationships': {
                        'type': 'object',
                        'additionalProperties': False
                    }
                },
                'required': ['type'],
                'additionalProperties': False
            }
        },
        'required': ['data'],
        'additionalProperties': False
    }

    @classmethod
    def get_urlpatterns(cls):
        return [
            path('v1/' + cls.basename + '/', cls.dispatch),
            path('v1/' + cls.basename + '/<id>/', cls.dispatch)
        ]

    @classmethod
    def __create(cls, request):

        # Parse the JSON:API data
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            raise RequestBodyJsonDecodeError() # TODO: Give more error details

        # Validate the JSON:API data
        try:
            jsonschema.validate(instance=data, schema=cls.__create_schema)
        except jsonschema.exceptions.ValidationError:
            raise RequestBodyJsonSchemaError() # TODO: Give more error details

        # Normalize the JSON:API data
        model_data = data['data']
        if 'attributes' not in model_data:
            model_data['attributes'] = {}
        if 'relationships' not in model_data:
            model_data['relationships'] = {}

        # Create the model
        model = cls.model()
        model._jsonapi_from_data(model_data)

        # Validate the model
        try:
            model.full_clean()
        except ValidationError as error:

            # Get the field name and error
            field_name = next(iter(error.error_dict))
            field_error = error.error_dict[field_name][0]

            # If the error is not recognized, don't handle it
            if field_error.code not in VALIDATION_ERRORS:
                raise error

            # Convert the error to a bad request error
            meta = {
                'attribute': field_name
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
            raise VALIDATION_ERRORS[field_error.code](meta=meta)

        # Save the model
        model.jsonapi_pre_save()
        model.save()
        model.jsonapi_post_save()

        # Return the model data
        return JsonResponse({
            'data': model._jsonapi_to_data()
        })

    @classmethod
    def __delete(cls, request, id):
        raise RequestMethodNotAllowedError()

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
        raise RequestMethodNotAllowedError()

    @classmethod
    def __list(cls, request):
        raise RequestMethodNotAllowedError()

    @classmethod
    def __update(cls, request, id):
        raise RequestMethodNotAllowedError()
