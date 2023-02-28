# Django
from django.http import JsonResponse
from django.utils.text import camel_case_to_spaces


class ErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, BadRequestError):
            class_name = camel_case_to_spaces(
                exception.__class__.__name__).replace(' ', '_')
            error_data = {
                'status': '400',
                'code': class_name
            }
            if exception.meta is not None:
                error_data['meta'] = exception.meta
            response = JsonResponse({
                'errors': [error_data]
            }, status=400)
            response['Cache-Control'] = 'no-cache'
            return response


class BadRequestError(Exception):
    def __init__(self, meta=None):
        self.meta = meta


class ModelAttributeInvalidError(BadRequestError):
    pass


class ModelAttributeRequiredError(BadRequestError):
    pass


class ModelAttributeTooLongError(BadRequestError):
    pass


class ModelAttributeTooShortError(BadRequestError):
    pass


class RequestBodyJsonDecodeError(BadRequestError):
    pass


class RequestBodyJsonSchemaError(BadRequestError):
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
