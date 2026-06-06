from django.urls import path
from .views import ReportesExportAPIView

urlpatterns = [
    path('export/', ReportesExportAPIView.as_view(), name='reportes-export'),
]