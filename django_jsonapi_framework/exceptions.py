# Django
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.utils.text import camel_case_to_spaces


"""
Django middleware class that intercepts instances of Django JSON:API Framework
errors and handles the errors by returning a structured response from the API
endpoint.
"""
class ErrorMiddleware:
    def __init__(self, get_response):
        """Initializes the Django middleware class."""
        self.get_response = get_response

    def __call__(self, request):
        """Handles the Django request.

        Triggered by Django to allow the middleware to add logic before and
        after the request is handled.
        """
        return self.get_response(request)

    def process_exception(self, request, exception):
        """Processes any exception that was raised during handling of the
        Django request.

        Triggered by Django to allow the middleware to handle errors that were
        raised during the handling of the Django request.
        """

        # Convert the error to a JSONApiError if it is supported
        if isinstance(exception, ValidationError):

            # Get the field name and error
            field_name = next(iter(exception.error_dict))
            field_exception = exception.error_dict[field_name][0]

            # Convert the error to a bad request error if recognized
            VALIDATION_ERRORS = {
                'null': ModelAttributeRequiredError,
                'blank': ModelAttributeTooShortError,
                'min_length': ModelAttributeTooShortError,
                'max_length': ModelAttributeTooLongError,
                'invalid': ModelAttributeInvalidError,
                'unique': ModelAttributeInvalidError,
                'unique_together': ModelFieldsUniqueTogetherError
            }
            if field_exception.code in VALIDATION_ERRORS:
                meta = {
                    'field': field_name
                }
                if field_exception.code == 'blank':
                    meta = {
                        'field': field_name,
                        'min_length': 1
                    }
                    for validator in model._meta.get_field(
                            field_name).validators:
                        if isinstance(validator, MinLengthValidator):
                            meta['min_length'] = validator.limit_value
                elif field_exception.code == 'min_length':
                    meta = {
                        'field': field_name,
                        'min_length': field_exception.params['limit_value']
                    }
                elif field_exception.code == 'max_length':
                    meta = {
                        'field': field_name,
                        'max_length': field_exception.params['limit_value']
                    }
                elif field_exception.code == 'unique_together':
                    meta = {
                        'fields': field_exception.params['unique_check']
                    }
                exception = VALIDATION_ERRORS[field_exception.code](meta=meta)

        # If the error is an instance of the JSONAPIError class
        if isinstance(exception, JSONAPIError):

            # If the error is an instance of the NoContentError class,
            # return an empty response
            if isinstance(exception, NoContentError):
                return HttpResponse(status=exception.status)

            # Convert the error class name to snake case and use it as the
            # error code in the error response data
            class_name = camel_case_to_spaces(
                exception.__class__.__name__).replace(' ', '_')
            error_response_data = {
                'code': class_name
            }

            # If the error has metadata, add it to the error data
            if exception.meta is not None:
                error_response_data['meta'] = exception.meta

            # Return the error response
            response = JsonResponse({
                'errors': [error_response_data]
            }, status=exception.status)
            response['Cache-Control'] = 'no-cache'
            return response

"""The base class for Django JSON:API Framework errors."""
class JSONAPIError(Exception):
    status = None
    def __init__(self, meta=None):
        self.meta = meta


"""Indicates a bad request was given."""
class BadRequestError(JSONAPIError):
    status = 400


"""Indicates a requested resource was not found."""
class NotFoundError(JSONAPIError):
    status = 404


"""Not actually an error, but a utility class used to return an empty response.
"""
class NoContentError(JSONAPIError):
    status = 204


"""The base class for model errors."""
class ModelError(JSONAPIError):
    pass


"""Indicates a model attribute is invalid."""
class ModelAttributeInvalidError(ModelError):
    pass


"""Indicates a model attribute is not allowed."""
class ModelAttributeNotAllowedError(ModelError):
    pass


"""Indicates a model attribute is required."""
class ModelAttributeRequiredError(ModelError):
    pass


"""Indicates a model attribute is too long."""
class ModelAttributeTooLongError(ModelError):
    pass


"""Indicates a model attribute is too short."""
class ModelAttributeTooShortError(ModelError):
    pass


"""Indicates a list of model fields (attributes or relationships) should be
unique together but aren't.
"""
class ModelFieldsUniqueTogetherError(ModelError):
    pass


"""Indicates an inconsistency between the model id in the request url and
request body.
"""
class ModelIdDoesNotMatchError(ModelError):
    pass


"""Indicated the model id is required but was not given."""
class ModelIdRequiredError(ModelError):
    pass


"""Indicates a model is not found, or that you don't have permission to view
it. In the latter case, the framework will pretend it doesn't exist (for
privacy reasons).
"""
class ModelNotFoundError(ModelError):
    pass


"""Indicates a model relationship is not allowed."""
class ModelRelationshipNotAllowedError(ModelError):
    pass


"""Indicates a referenced model in a model relationship does not exist, or that
you don't have enough permission to view it.  In the latter case, the framework
will pretend it doesn't exist (for privacy reasons).
"""
class ModelRelationshipInvalidError(ModelError):
    # TODO: Error is not thrown by framework yet
    pass


"""Indicates a model relationship is required."""
class ModelRelationshipRequiredError(ModelError):
    # TODO: Error is not thrown by framework yet
    pass


"""Indicates a model type is invalid."""
class ModelTypeInvalidError(ModelError):
    pass


"""Indicates the request body contains invalid JSON."""
class RequestBodyJsonDecodeError(BadRequestError):
    pass


"""Indicates the request body JSON does not adhere to the JSON:API format."""
class RequestBodyJsonSchemaError(BadRequestError):
    pass


"""Indicates a request body was given but is not allowed."""
class RequestBodyNotAllowedError(BadRequestError):
    pass


"""Indicates a request header is invalid."""
class RequestHeaderInvalidError(BadRequestError):
    pass


"""Indicates a request header is not allowed."""
class RequestMethodNotAllowedError(BadRequestError):
    pass
