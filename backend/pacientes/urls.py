from django.urls import path
from .views import ETLRunView, PacientesUploadView, ETLHistoryView

urlpatterns = [
    path('etl/run/', ETLRunView.as_view(), name='etl-run'),
    path('pacientes/upload/', PacientesUploadView.as_view(), name='pacientes-upload'),
    path('etl/history/', ETLHistoryView.as_view(), name='etl-history'),
]
