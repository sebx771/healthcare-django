from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authentication.permissions import IsAdministrador, IsMedico, IsAnalista
from pacientes.models import Paciente
from .serializers import ReporteExportSerializer
from .services import ReportesService

class ReportesExportAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador | IsMedico | IsAnalista]

    def get(self, request, *args, **kwargs):
        serializer = ReporteExportSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        validated = serializer.validated_data
        queryset = Paciente.objects.all()

        search_term = validated.get('search')
        if search_term:
            queryset = queryset.filter(
                Q(nombres__icontains=search_term) |
                Q(apellidos__icontains=search_term) |
                Q(id_paciente__icontains=search_term)
            )

        riesgo = validated.get('riesgo')
        if riesgo:
            queryset = queryset.filter(riesgo_enfermedad__iexact=riesgo)

        fecha_desde = validated.get('fecha_desde')
        if fecha_desde:
            queryset = queryset.filter(fecha_consulta__gte=fecha_desde)

        fecha_hasta = validated.get('fecha_hasta')
        if fecha_hasta:
            queryset = queryset.filter(fecha_consulta__lte=fecha_hasta)

        formato = validated['format']
        return ReportesService.crear_reporte(formato, queryset)