from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from authentication.permissions import IsAdministrador, IsMedico
from ..models import Paciente
from ..serializers import PacienteSerializer

class PacienteListAPIView(generics.ListAPIView):
    serializer_class = PacienteSerializer
    permission_classes = [IsAuthenticated, IsAdministrador | IsMedico]

    def get_queryset(self):
        queryset = Paciente.objects.all()
        search_query = self.request.query_params.get('search', None)
        riesgo_query = self.request.query_params.get('riesgo', None)

        if search_query:
            # Busca coincidencia parcial en nombres/apellidos o coincidencia exacta en id_paciente
            queryset = queryset.filter(
                Q(nombres__icontains=search_query) |
                Q(apellidos__icontains=search_query) |
                Q(id_paciente__icontains=search_query)
            )

        if riesgo_query:
            # Filtro exacto (insensible a mayúsculas) por nivel de riesgo (Bajo, Medio, Alto, Crítico)
            queryset = queryset.filter(riesgo_enfermedad__iexact=riesgo_query)

        return queryset


class PacienteDetailAPIView(generics.RetrieveAPIView):
    queryset = Paciente.objects.all()
    serializer_class = PacienteSerializer
    permission_classes = [IsAuthenticated, IsAdministrador | IsMedico]
