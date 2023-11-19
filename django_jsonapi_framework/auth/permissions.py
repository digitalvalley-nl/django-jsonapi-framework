# Django
from django.db.models import Q

"""Permission class used to make sure a model can only be accessed if the model
adheres to all of the provided sub conditions related to the currently
authenticated user, or in the case of a queryset, that models that don't match
are filtered out.
"""
class AllOf:
    def __init__(self, *conditions):
        """Initializes the permission class."""
        self.__conditions = conditions
        if len(conditions) < 2:
            raise ValueError('AllOf requires at least 2 conditions')

    def check_model(self, model, user):
        """Returns true if the user can access the model, false otherwise."""
        for condition in self.__conditions:
            if not condition.check_model(model, user):
                return False
        return True

    def check_queryset(self, queryset, user):
        """Filters out models the user is not allowed to access."""
        filter = self.__conditions[0](queryset, user)
        for condition in self.__conditions[1:]:
            filter &= condition(queryset, user)
        return filter


"""Permission class used to make sure a model can only be accessed if the model
adheres to any of the provided sub conditions related to the currently
authenticated user, or in the case of a queryset, that models that don't match
are filtered out.
"""
class AnyOf:
    def __init__(self, *conditions):
        """Initializes the permission class."""
        self.__conditions = conditions
        if len(conditions) < 2:
            raise ValueError('AnyOf requires at least 2 conditions')

    def check_model(self, model, user):
        """Returns true if the user can access the model, false otherwise."""
        for condition in self.__conditions:
            if condition.check_model(model, user):
                return True
        return False

    def check_queryset(self, queryset, user):
        """Filters out models the user is not allowed to access."""
        filter = self.__conditions[0](queryset, user)
        for condition in self.__conditions[1:]:
            filter |= condition(queryset, user)
        return filter


"""Permission class used to make sure a model can only be accessed if a model
field is equal to a field of the currently authenticated user, or in the case
of a queryset, that models that don't match are filered out.
"""
class ModelFieldIsEqualToOwnField:
    def __init__(self, field, own_field):
        """Initializes the permission class."""
        self.__field = field
        self.__own_field = own_field

    def check_model(self, model, user):
        """Returns true if the user can access the model, false otherwise."""
        if user is None:
            return False
        value = getattr(model, self.__field)
        if value == getattr(user, self.__own_field):
            return True
        return False

    def check_queryset(self, queryset, user):
        """Filters out models the user is not allowed to access."""
        if user is None:
            return Q(pk__in=[])
        kwargs = {
            self.__field: getattr(user, self.__own_field)
        }
        return Q(**kwargs)


"""Permission class used to make sure a model can only be accessed if the
model's organization id is equal to the organization id of the currently
authenticated user, or in the case of a queryset, that models that don't match
are filered out.
"""
class IsOwnOrganization(ModelFieldIsEqualToOwnField):
    def __init__(self):
        """Initializes the permission class."""
        super().__init__('organization_id', 'organization_id')


"""Permission class used to make sure a model can only be accessed if the
the currently authenticated user has a permission, or in the case of a
queryset, that an empty queryset is returned if the user does not have the
permission.
"""
class UserHasPermission:
    def __init__(self, key):
        """Initializes the permission class."""
        self.__key = key

    def check_model(self, model, user):
        """Returns true if the user can access the model, false otherwise."""
        if user is not None and user.has_permission(self.__key):
            return True
        return False

    def check_queryset(self, queryset, user):
        """Filters out models the user is not allowed to access."""
        if user.has_permission(self.__key):
            return ~Q(pk__in=[])
        return Q(pk__in=[])
