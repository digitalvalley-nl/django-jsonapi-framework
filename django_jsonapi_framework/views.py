# Python Standard Library
import copy
import json
from pathlib import Path

# Django
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.http import HttpResponse, JsonResponse
from django.urls import path
from django.db import transaction
from django.db.models.fields import Field

# Django JSON:API Framework - Core
from django_jsonapi_framework.exceptions import (
    ModelAttributeNotAllowedError,
    ModelAttributeRequiredError,
    ModelAttributeTooLongError,
    ModelAttributeTooShortError,
    ModelRelationshipNotAllowedError,
    ModelIdDoesNotMatchError,
    ModelIdRequiredError,
    ModelNotFoundError,
    ModelTypeInvalidError,
    RequestBodyJsonDecodeError,
    RequestBodyJsonSchemaError,
    RequestBodyNotAllowedError,
    RequestHeaderInvalidError,
    RequestMethodNotAllowedError
)
from django_jsonapi_framework.utils import (
    camel_case_to_snake_case,
    get_class_by_fully_qualified_name,
    snake_case_to_camel_case
)

# JSON Schema
import jsonschema


"""Class that represents a JSON:API resource."""
class JSONAPIResource:

    """Defines the basename of the resource."""
    basename = None

    """Defines the model that is mapped to the resource."""
    model = None

    """The profile used to configure the create action of the resource."""
    create_profile = None

    """The profile used to configure the read action of the resource."""
    read_profile = None

    """The profile used to configure the update action of the resource."""
    update_profile = None

    """The profile used to configure the delete action of the resource."""
    delete_profile = None

    """Loads the JSON:API Schema in 2 variations: create and update."""
    __schemas = {}
    with open(str(Path(__file__).resolve().parent) + '/schema.json') as file:
        __schemas['update'] = json.loads(file.read())
    __schemas['create'] = copy.deepcopy(__schemas['update'])
    __schemas['create']['definitions']['resource']['required'].remove('id')
    del __schemas['create']['definitions']['resource']['properties']['id']

    @classmethod
    def dispatch(cls, request, id=None):
        """Dispatches an incoming request to the appropriate handler for the
        REST method."""
        if request.method == 'GET':
            if id is None:
                return cls.__handle_list_request(request)
            return cls.__handle_get_request(request, id)
        if request.method == 'POST':
            return cls.__handle_create_request(request)
        if request.method == 'PATCH':
            return cls.__handle_update_request(request, id)
        if request.method == 'DELETE':
            return cls.__handle_delete_request(request, id)
        raise RequestMethodNotAllowedError()

    @classmethod
    def get_urlpatterns(cls):
        """Returns the urlpatterns for the resource."""
        return [
            path(cls.basename + '/', cls.dispatch),
            path(cls.basename + '/<id>/', cls.dispatch)
        ]

    @classmethod
    def __get_model(cls, id):
        """Retrieves a model from the database by id."""
        try:
            model = cls.model.objects.get(id=id)
        except cls.model.DoesNotExist:
            raise ModelNotFoundError()
        return model

    @classmethod
    def __handle_create_request(cls, request):
        """Handles an incoming create request."""

        # Parse and validate the request
        cls.__validate_request_method('create')
        cls.__validate_request_headers(request)
        body = cls.__parse_request_body(request)
        cls.__validate_request_body(body, cls.create_profile)
        resource = body['data']

        # Create, populate, validate and save the model
        model = cls.model()
        cls.__populate_model_from_resource(
            model=model,
            resource=resource,
            profile=cls.create_profile
        )
        with transaction.atomic():
            model.full_clean()
            model.save()

        # If configured by the create profile, render the model to a resource
        # and return it in the response data
        if cls.create_profile.show_response:
            return JsonResponse({
                'data': cls.__render_model_to_resource(
                    model=model,
                    profile=cls.read_profile
                )
            })

        # Otherwise, return an empty response
        return HttpResponse(status=204)

    @classmethod
    def __handle_delete_request(cls, request, id):
        """Handles an incoming delete request."""

        # Parse and validate the request
        cls.__validate_request_method('delete')
        cls.__validate_request_headers(request)
        cls.__validate_request_body_is_empty(request)

        # Get and delete the model
        model = cls.__get_model(id)
        model.delete()

        # Return an empty response
        return HttpResponse(status=204)

    @classmethod
    def __handle_get_request(cls, request, id):
        """Handles an incoming get request."""

        # Parse and validate the request
        cls.__validate_request_method('read')
        cls.__validate_request_headers(request)
        cls.__validate_request_body_is_empty(request)

        # Get the model
        model = cls.__get_model(id)

        # Render the model to a resource and return it in the response data
        return JsonResponse({
            'data': cls.__render_model_to_resource(
                model=model,
                profile=cls.read_profile
            )
        })

    @classmethod
    def __handle_list_request(cls, request):
        """Handles an incoming list request."""

        # Parse and validate the request
        cls.__validate_request_method('read')
        cls.__validate_request_headers(request)
        cls.__validate_request_body_is_empty(request)

        # List the models
        models = cls.model.objects.all()

        # TODO: Support filter options

        # Render the models to a list of resources and return it in the
        # response data
        return JsonResponse({
            'data': list(
                map(
                    lambda model: cls.__render_model_to_resource(
                        model=model,
                        profile=read_profile
                    ),
                    models
                )
            )
        })

    @classmethod
    def __handle_update_request(cls, request, id):
        """Handles an incoming update request."""

        # Parse and validate the request
        cls.__validate_request_method('update')
        cls.__validate_request_headers(request)
        body = cls.__parse_request_body(request)
        cls.__validate_request_body(body, cls.update_profile, id)
        resource = body['data']

        # Get, populate, validate and save the model
        model = cls.__get_model(id)
        update_profile = cls.update_profile
        cls.__populate_model_from_resource(
            model=model,
            resource=resource,
            profile=cls.update_profile
        )
        with transaction.atomic():
            model.full_clean()
            model.save()

        # If configured by the update profile, render the model to a resource
        # and return it in the response data
        if cls.update_profile.show_response:
            return JsonResponse({
                'data': cls.__render_model_to_resource(
                    model=model,
                    profile=cls.read_profile
                )
            })

        # Otherwise, return an empty response
        return HttpResponse(status=204)

    @classmethod
    def __parse_request_body(cls, request):
        """Parses the request body json."""
        try:
            body = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            raise RequestBodyJsonDecodeError() # TODO: Give more error details
        return body

    @classmethod
    def __populate_model_from_resource(cls, model, resource, profile):
        """Populates a model from a JSON:API resource using a profile."""

        # Populate the attributes
        if 'attributes' in resource:
            for attribute_name, attribute_value in resource['attributes'].items():
                attribute_name = camel_case_to_snake_case(attribute_name)
                if attribute_name in profile.attribute_mappings:
                    attribute_name = profile.attribute_mappings[attribute_name]
                setattr(model, attribute_name, attribute_value)

        # Populate the relationships
        if 'relationships' in resource:
            for relationship_name, relationship_value \
                    in resource['relationships'].items():
                relationship_name = camel_case_to_snake_case(relationship_name)
                if relationship_value['data'] is None:
                    setattr(model, relationship_name, None)
                else:
                    resource_class = profile.relationships[relationship_name]
                    if isinstance(resource_class, str):
                        resource_class = get_class_by_fully_qualified_name(
                            resource_class
                        )
                    relationship_instance = resource_class.model.objects.get(
                        id=relationship_value['data']['id']
                    )
                    setattr(model, relationship_name, relationship_instance)

    @classmethod
    def __render_model_to_resource(cls, model, profile):
        """Renders a model to a JSON:API resource using a profile."""

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
            'id': model.id,
            'type': model.__class__.__name__,
        }
        if len(attributes.keys()) > 0:
            resource['attributes'] = attributes
        if len(relationships.keys()) > 0:
            resource['relationships'] = relationships

        return resource

    @classmethod
    def __validate_request_body(cls, body, profile, id=None):
        """Validates the request body."""

        # Validate the body against the JSON:API schema
        if id is None:
            schema = cls.__schemas['create']
        else:
            schema = cls.__schemas['update']
        try:
            jsonschema.validate(instance=body, schema=schema)
        except jsonschema.exceptions.ValidationError:
            raise RequestBodyJsonSchemaError() # TODO: Give more error details

        # Validate the resource type
        resource = body['data']
        if resource['type'] != cls.model.__name__:
            raise ModelTypeInvalidError()

        # Validate the resource id
        if id is not None:
            if 'id' not in resource:
                ModelIdRequiredError()
            if resource['id'] != id:
                raise ModelIdDoesNotMatchError()

        # Validate the resource attributes
        if 'attributes' in resource:
            for attribute_name, attribute_value \
                    in resource['attributes'].items():
                attribute_name = camel_case_to_snake_case(attribute_name)
                if attribute_name not in profile.attributes:
                    raise ModelAttributeNotAllowedError({
                        'key': attribute_name
                    })

        # Validate the resource relationships
        if 'relationships' in resource:
            for relationship_name, relationship_value \
                    in resource['relationships'].items():
                relationship_name = camel_case_to_snake_case(relationship_name)
                if relationship_name not in profile.relationships:
                    raise ModelRelationshipNotAllowedError({
                        'key': relationship_name
                    })

    @classmethod
    def __validate_request_body_is_empty(cls, request):
        """Validates to make sure the request body is empty."""
        if len(request.body) > 0:
            raise RequestBodyNotAllowedError()

    @classmethod
    def __validate_request_headers(cls, request):
        """Validates to request headers."""
        if len(request.body) > 0 \
                and request.headers['Content-Type'] != 'application/vnd.api+json':
            raise RequestHeaderInvalidError({
                'key': 'Content-Type',
                'value': request.headers['Content-Type']
            })

    @classmethod
    def __validate_request_method(cls, action):
        """Validates to request method is allowed."""
        if getattr(cls, action + '_profile') is None:
            raise RequestMethodNotAllowedError()


"""Class used to configure the behaviour of the request methods of a
JSON:API resource.
"""
class JSONAPIResourceProfile:
    def __init__(
        self,
        attributes=None,
        attribute_mappings=None,
        relationships=None,
        show_response=True
    ):
        """Initialized the profile."""
        self.attributes = attributes if attributes is not None else []
        self.attribute_mappings = \
            attribute_mappings if attribute_mappings is not None else {}
        self.relationships = relationships if relationships is not None else {}
        self.show_response = show_response
