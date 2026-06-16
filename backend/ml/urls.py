from django.urls import path
from .views import PrediccionRiesgoAPIView, MetricasMLAPIView

urlpatterns = [
    path('prediccion/', PrediccionRiesgoAPIView.as_view(), name='ml-predict'),
    path('metricas/', MetricasMLAPIView.as_view(), name='ml-metricas'),
]

