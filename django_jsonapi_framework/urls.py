# Django
from django.apps import apps

# Django JSON:API Framework
from django_jsonapi_framework.models import JSONAPIModel
from django_jsonapi_framework.views import JSONAPIView


# Automatically add the urlpatterns for all JSONAPIModel subclasses in installed apps
urlpatterns = []
models = apps.get_models()
for model in models:
    if issubclass(model, JSONAPIModel):
        view = JSONAPIView()
        view.model = model
        urlpatterns += view.get_urlpatterns()
