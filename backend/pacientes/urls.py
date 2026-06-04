from django.urls import path
from .views import ETLRunView, PacientesUploadView, ETLHistoryView, PacienteListAPIView, PacienteDetailAPIView

urlpatterns = [
    path('etl/run/', ETLRunView.as_view(), name='etl-run'),
    path('pacientes/upload/', PacientesUploadView.as_view(), name='pacientes-upload'),
    path('etl/history/', ETLHistoryView.as_view(), name='etl-history'),
    path('pacientes/', PacienteListAPIView.as_view(), name='paciente-list'),
    path('pacientes/<int:pk>/', PacienteDetailAPIView.as_view(), name='paciente-detail'),
]
