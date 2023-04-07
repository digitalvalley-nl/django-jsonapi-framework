# Django
from django.db.models import Q


class HasAll:
    def __init__(self, *conditions):
        self.__conditions = conditions
        if len(conditions) < 2:
            raise ValueError('HasAll requires at least 2 conditions')

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


class HasAny:
    def __init__(self, *conditions):
        self.__conditions = conditions
        if len(conditions) < 2:
            raise ValueError('HasAny requires at least 2 conditions')

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


class HasOrganization:
    def __init__(self, field='organization_id'):
        self.__field = field

    def check_model(self, model, user):
        if user is None:
            return False
        value = getattr(model, self.__field)
        if value == user.organization_id:
            return True
        return False

    def check_queryset(self, queryset, user):
        if user is None:
            return Q(pk__in=[])
        kwargs = {
            self.__field: user.organization_id
        }
        return Q(**kwargs)


class HasPermission:
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
    def __init__(self, condition=None, attributes=None, relationships=None):
        self.__condition = condition
        self.attributes = attributes if attributes is not None else []
        self.relationships = relationships if relationships is not None else []
