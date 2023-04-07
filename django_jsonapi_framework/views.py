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
    ModelAttributeRequiredError,
    ModelAttributeTooLongError,
    ModelAttributeTooShortError,
    ModelIdDoesNotMatchError,
    ModelNotFoundError,
    ModelTypeInvalidError,
    RequestBodyJsonDecodeError,
    RequestBodyJsonSchemaError,
    RequestHeaderInvalidError,
    RequestMethodNotAllowedError,
    VALIDATION_ERRORS
)
from django_jsonapi_framework.permissions import ProfileResolver

# JSON Schema
import jsonschema


class JSONAPIView:

    __schemas = {}
    with open(str(Path(__file__).resolve().parent) + '/schema.json') as file:
        __schemas['update'] = json.loads(file.read())
    __schemas['create'] = copy.deepcopy(__schemas['update'])
    __schemas['create']['definitions']['resource']['required'].remove('id')
    del __schemas['create']['definitions']['resource']['properties']['id']

    def get_urlpatterns(self):
        return [
            path(self.model.JSONAPIMeta.resource_name + '/', self.dispatch),
            path(self.model.JSONAPIMeta.resource_name + '/<id>/', self.dispatch)
        ]

    def __create(self, request):

        # Parse the request
        self.__validate_request_headers(request)
        data = self.__parse_request_body(request, 'create')
        model_data = self.__parse_model_data(data['data'])
        if model_data['type'] != self.model.__name__:
            raise ModelTypeInvalidError()

        # Create the model
        model = self.model()
        create_profile = model.JSONAPIMeta.create
        if isinstance(create_profile, ProfileResolver):
            create_profile = create_profile.resolve(None)
        model.from_jsonapi_resource(model_data, create_profile)
        self.__validate_model(model)
        model.save()

        # Return the model data
        if create_profile.show_response:
            read_profile = model.JSONAPIMeta.read
            if isinstance(read_profile, ProfileResolver):
                read_profile = read_profile.resolve(None)
            return JsonResponse({
                'data': model.to_jsonapi_resource(read_profile)
            })
        else:
            return HttpResponse(status=204)

    def __delete(self, request, id):
        model = self.__get_model(id)
        model.delete()
        return HttpResponse(status=204)

    def dispatch(self, request, id=None):
        if request.method == 'GET':
            if id is None:
                return self.__list(request)
            return self.__get(request, id)
        if request.method == 'POST':
            return self.__create(request)
        if request.method == 'PATCH':
            return self.__update(request, id)
        if request.method == 'DELETE':
            return self.__delete(request, id)
        raise RequestMethodNotAllowedError()

    def __get(self, request, id):
        model = self.__get_model(id)
        read_profile = model.JSONAPIMeta.read
        if isinstance(read_profile, ProfileResolver):
            read_profile = read_profile.resolve(None)
        return JsonResponse({
            'data': model.to_jsonapi_resource(read_profile)
        })

    def __list(self, request):
        models = self.model.objects.all()
        read_profile = self.model.JSONAPIMeta.read
        if isinstance(read_profile, ProfileResolver):
            read_profile = read_profile.resolve(None)
        return JsonResponse({
            'data': list(
                map(
                    lambda model: model.to_jsonapi_resource(read_profile),
                    models
                )
            )
        })

    def __update(self, request, id):

        # Parse the request
        self.__validate_request_headers(request)
        data = self.__parse_request_body(request, 'update')
        model_data = self.__parse_model_data(data['data'])
        if model_data['type'] != self.model.__name__:
            raise ModelTypeInvalidError()
        if model_data['id'] != id:
            raise ModelIdDoesNotMatchError()

        # Create the model
        model = self.__get_model(id)
        update_profile = model.JSONAPIMeta.update
        if isinstance(update_profile, ProfileResolver):
            update_profile = update_profile.resolve(None)
        model.from_jsonapi_resource(model_data, update_profile)
        self.__validate_model(model)
        model.save()

        # Return the model data
        if update_profile.show_response:
            read_profile = model.JSONAPIMeta.read
            if isinstance(read_profile, ProfileResolver):
                read_profile = read_profile.resolve(None)
            return JsonResponse({
                'data': model.to_jsonapi_resource(read_profile)
            })
        else:
            return HttpResponse(status=204)

    def __get_model(self, id):
        try:
            model = self.model.objects.get(id=id)
        except self.model.DoesNotExist:
            raise ModelNotFoundError()
        return model

    def __validate_request_headers(self, request):
        if request.headers['Content-Type'] != 'application/vnd.api+json':
            raise RequestHeaderInvalidError({
                'key': 'Content-Type',
                'value': request.headers['Content-Type']
            })

    def __parse_request_body(self, request, schema):
        # Parse the JSON:API data
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            raise RequestBodyJsonDecodeError() # TODO: Give more error details

        # Validate the JSON:API data
        try:
            jsonschema.validate(instance=data, schema=self.__schemas[schema])
        except jsonschema.exceptions.ValidationError:
            raise RequestBodyJsonSchemaError() # TODO: Give more error details

        return data

    def __parse_model_data(self, model_data):
        if 'attributes' not in model_data:
            model_data['attributes'] = {}
        if 'relationships' not in model_data:
            model_data['relationships'] = {}
        return model_data

    def __validate_model(self, model):
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
            raise VALIDATION_ERRORS[field_error.code](meta=meta)
