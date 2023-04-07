import re


CAMEL_CASE_TO_SNAKE_CASE_REGEX = re.compile(r'(?<!^)(?=[A-Z])')


def camel_case_to_snake_case(value):
    return CAMEL_CASE_TO_SNAKE_CASE_REGEX.sub('_', value).lower()


def snake_case_to_camel_case(value):
    components = value.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])
