from django.urls import path
from .views import PrediccionRiesgoAPIView

urlpatterns = [
    path('prediccion/', PrediccionRiesgoAPIView.as_view(), name='ml-predict'),
]