from django.urls import path
from .views import ETLRunView, PacientesUploadView, ETLHistoryView, PacienteListAPIView, PacienteDetailAPIView, PacienteRevisarView, PacienteNoRevisarView
from .views.medico_revision_update_views import PacienteUpdateAPIView, PacienteRevisarYActualizarView

urlpatterns = [
    path('etl/run/', ETLRunView.as_view(), name='etl-run'),
    path('pacientes/upload/', PacientesUploadView.as_view(), name='pacientes-upload'),
    path('etl/history/', ETLHistoryView.as_view(), name='etl-history'),
    path('pacientes/', PacienteListAPIView.as_view(), name='paciente-list'),
    path('pacientes/<int:pk>/', PacienteDetailAPIView.as_view(), name='paciente-detail'),
    path('pacientes/<int:pk>/update/', PacienteUpdateAPIView.as_view(), name='paciente-update'),
    path('pacientes/<int:pk>/revisar-y-actualizar/', PacienteRevisarYActualizarView.as_view(), name='paciente-revisar-y-actualizar'),
    path('pacientes/<int:pk>/revisar/', PacienteRevisarView.as_view(), name='paciente-revisar'),
    path('pacientes/<int:pk>/no-revisar/', PacienteNoRevisarView.as_view(), name='paciente-no-revisar'),
]
