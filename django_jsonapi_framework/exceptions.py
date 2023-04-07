# Django
from django.http import JsonResponse
from django.utils.text import camel_case_to_spaces


class ErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, JSONAPIError):
            class_name = camel_case_to_spaces(
                exception.__class__.__name__).replace(' ', '_')
            error_data = {
                'code': class_name
            }
            if exception.meta is not None:
                error_data['meta'] = exception.meta
            response = JsonResponse({
                'errors': [error_data]
            }, status=exception.status)
            response['Cache-Control'] = 'no-cache'
            return response


class JSONAPIError(Exception):
    status = None
    def __init__(self, meta=None):
        self.meta = meta


class BadRequestError(JSONAPIError):
    status = 400

class NotFoundError(JSONAPIError):
    status = 404


class ModelAttributeInvalidError(BadRequestError):
    pass


class ModelAttributeNotAllowedError(BadRequestError):
    pass


class ModelAttributeRequiredError(BadRequestError):
    pass


class ModelAttributeTooLongError(BadRequestError):
    pass


class ModelAttributeTooShortError(BadRequestError):
    pass


class ModelIdDoesNotMatchError(BadRequestError):
    pass


class ModelNotFoundError(NotFoundError):
    pass


class ModelRelationshipNotAllowedError(BadRequestError):
    pass


class ModelRelationshipInvalidError(BadRequestError):
    pass


class ModelRelationshipRequiredError(BadRequestError):
    pass


class ModelTypeInvalidError(BadRequestError):
    pass


class RequestBodyJsonDecodeError(BadRequestError):
    pass


class RequestBodyJsonSchemaError(BadRequestError):
    pass


class RequestHeaderInvalidError(BadRequestError):
    pass


class RequestMethodNotAllowedError(BadRequestError):
    pass


VALIDATION_ERRORS = {
    'null': ModelAttributeRequiredError,
    'blank': ModelAttributeTooShortError,
    'min_length': ModelAttributeTooShortError,
    'max_length': ModelAttributeTooLongError,
    'invalid': ModelAttributeInvalidError
}
