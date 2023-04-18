# Django
from django.db.models import Q


class AllOf:
    def __init__(self, *conditions):
        self.__conditions = conditions
        if len(conditions) < 2:
            raise ValueError('AllOf requires at least 2 conditions')

    def check_model(self, model, user):
        for condition in self.__conditions:
            if not condition.check_model(model, user):
                return False
        return True

    def check_queryset(self, queryset, user):
        filter = self.__conditions[0](queryset, user)
        for condition in self.__conditions[1:]:
            filter &= condition(queryset, user)
        return filter


class AnyOf:
    def __init__(self, *conditions):
        self.__conditions = conditions
        if len(conditions) < 2:
            raise ValueError('AnyOf requires at least 2 conditions')

    def check_model(self, model, user):
        for condition in self.__conditions:
            if condition.check_model(model, user):
                return True
        return False

    def check_queryset(self, queryset, user):
        filter = self.__conditions[0](queryset, user)
        for condition in self.__conditions[1:]:
            filter |= condition(queryset, user)
        return filter


class ModelFieldIsEqualToOwnField:
    def __init__(self, field, own_field):
        self.__field = field
        self.__own_field = own_field

    def check_model(self, model, user):
        if user is None:
            return False
        value = getattr(model, self.__field)
        if value == getattr(user, self.__own_field):
            return True
        return False

    def check_queryset(self, queryset, user):
        if user is None:
            return Q(pk__in=[])
        kwargs = {
            self.__field: getattr(user, self.__own_field)
        }
        return Q(**kwargs)


class ModelFieldIsEqualToValue:
    def __init__(self, field, value):
        self.__field = field
        self.__value = value

    def check_model(self, model, user):
        value = getattr(model, self.__field)
        if value == self.__value:
            return True
        return False

    def check_queryset(self, queryset, user):
        kwargs = {
            self.__field: self.__value
        }
        return Q(**kwargs)


class ModelFieldIsNone:
    def __init__(self, field):
        self.__field = field

    def check_model(self, model, user):
        value = getattr(model, self.__field)
        if value is None:
            return True
        return False

    def check_queryset(self, queryset, user):
        kwargs = {
            self.__field + '__isnull': True
        }
        return Q(**kwargs)


class ModelFieldIsNotNone:
    def __init__(self, field):
        self.__field = field

    def check_model(self, model, user):
        value = getattr(model, self.__field)
        if value is not None:
            return True
        return False

    def check_queryset(self, queryset, user):
        kwargs = {
            self.__field + '__isnull': False
        }
        return Q(**kwargs)


class UserHasGlobalPermission:
    def __init__(self, key):
        self.__key = key

    def check_model(self, model, user):
        if user is not None and user.has_permission(self.__key):
            return True
        return False

    def check_queryset(self, queryset, user):
        if user.has_permission(self.__key):
            return ~Q(pk__in=[])
        return Q(pk__in=[])


class UserHasPermissionInOrganizationOfModel:
    def __init__(self, key):
        self.__key = key

    def check_model(self, model, user):
        if user is not None and user.has_permission(self.__key):
            return True
        return False

    def check_queryset(self, queryset, user):
        if user.has_permission(self.__key):
            return ~Q(pk__in=[])
        return Q(pk__in=[])



class Profile:
    def __init__(
        self,
        condition=None,
        attributes=None,
        attribute_mappings=None,
        relationships=None,
        show_response=True
    ):
        self.__condition = condition
        self.attributes = attributes if attributes is not None else []
        self.attribute_mappings = \
            attribute_mappings if attribute_mappings is not None else {}
        self.relationships = relationships if relationships is not None else {}
        self.show_response = show_response

    def resolve(self, user):
        return self


class ProfileResolver:
    def __init__(self, *profiles):
        if len(profiles) < 2:
            raise ValueError('ProfileResolver requires at least 2 profiles')
        self.__profiles = profiles

    def resolve(self, user):
        # TODO: Check the conditions to find a profiles match
        return self.__profiles[0]
