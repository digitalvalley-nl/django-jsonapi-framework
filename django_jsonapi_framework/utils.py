# Python Standard Library
from importlib import import_module
import re

# Django
from django.core.exceptions import ValidationError


"""The regular expression used to convert camel case to snake case."""
__CAMEL_CASE_TO_SNAKE_CASE_REGEX = re.compile(r'(?<!^)(?=[A-Z])')


"""Utility method to converting camel case to snake case."""
def camel_case_to_snake_case(value):
    return __CAMEL_CASE_TO_SNAKE_CASE_REGEX.sub('_', value).lower()


"""Utility method for manually validating a Django field."""
def clean_field(model, field, value):
    try:
        field.clean(value, model)
    except ValidationError as error:
        error.error_dict = {
            'field_name': error.error_list
        }
        raise error


"""Utility method for dynamically importing a class."""
def get_class_by_fully_qualified_name(fully_qualified_name):
    parts = fully_qualified_name.split('.')
    module_path = ".".join(parts[:-1])
    return getattr(import_module(module_path), parts[-1])


"""Utility method to converting snake case to camel case."""
def snake_case_to_camel_case(value):
    components = value.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])
