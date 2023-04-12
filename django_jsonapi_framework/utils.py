import re


CAMEL_CASE_TO_SNAKE_CASE_REGEX = re.compile(r'(?<!^)(?=[A-Z])')


def camel_case_to_snake_case(value):
    return CAMEL_CASE_TO_SNAKE_CASE_REGEX.sub('_', value).lower()


def snake_case_to_camel_case(value):
    components = value.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def get_class_by_fully_qualified_name(fully_qualified_name):
    parts = fully_qualified_name.split('.')
    module_path = ".".join(parts[:-1])
    module = __import__(module_path)
    for component in parts[1:]:
        module = getattr(module, component)
    return module


def clean_field(self, field_name, field, value):
    try:
        field.clean(value, self)
    except ValidationError as error:
        error.error_dict = {
            'field_name': error.error_list
        }
        raise error
