from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import logging

from authentication.permissions import IsAdministrador, IsMedico, IsAnalista
from pacientes.models import Paciente
from .serializers import ReporteExportSerializer
from .services import ReportesService

logger = logging.getLogger(__name__)

class ReportesExportAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador | IsMedico | IsAnalista]

    def get(self, request, *args, **kwargs):
        logger.info(f"🔍 GET /api/reportes/export/ recibido")
        logger.info(f"   Query params: {dict(request.query_params)}")
        logger.info(f"   GET params: {dict(request.GET)}")
        logger.info(f"   Path: {request.path}")
        logger.info(f"   Full path: {request.get_full_path()}")
        
        serializer = ReporteExportSerializer(data=request.query_params)
        if not serializer.is_valid():
            logger.warning(f"   Serializer invalid: {serializer.errors}")
            return Response(serializer.errors, status=400)

        validated = serializer.validated_data
        logger.info(f"   Validated data: {validated}")
        
        queryset = Paciente.objects.all()

        search_term = validated.get('search')
        if search_term:
            queryset = queryset.filter(
                Q(nombres__icontains=search_term) |
                Q(apellidos__icontains=search_term)
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

        export_format = validated['export_format']
        logger.info(f"   Generando reporte en formato: {export_format}")
        return ReportesService.crear_reporte(export_format, queryset)