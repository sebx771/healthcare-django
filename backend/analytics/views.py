from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from authentication.permissions import IsAdministrador, IsMedico, IsAnalista
from .services import AnalyticsService

CALIDAD_CHOICES = {'todos', 'validos', 'criticos', 'sospechosos', 'inconsistentes'}
REVISADO_CHOICES = {'todos', 'si', 'no'}

class DashboardKPIsAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador | IsMedico | IsAnalista]

    def get(self, request, *args, **kwargs):
        try:
            calidad = request.query_params.get('calidad', 'todos')
            revisado = request.query_params.get('revisado', 'todos')

            if calidad not in CALIDAD_CHOICES:
                return Response({
                    "estado": "ERROR",
                    "detalle": f"calidad inválido. Opciones: {', '.join(sorted(CALIDAD_CHOICES))}"
                }, status=status.HTTP_400_BAD_REQUEST)
            if revisado not in REVISADO_CHOICES:
                return Response({
                    "estado": "ERROR",
                    "detalle": f"revisado inválido. Opciones: {', '.join(sorted(REVISADO_CHOICES))}"
                }, status=status.HTTP_400_BAD_REQUEST)

            filtrar_calidad = [] if calidad == 'todos' else [calidad]
            excluir_revisados = (revisado == 'no')

            data = AnalyticsService.obtener_kpis_descriptivos(
                filtrar_calidad=filtrar_calidad,
                excluir_revisados=excluir_revisados,
            )

            return Response({
                "estado": "EXITOSO",
                "datos": data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "estado": "ERROR",
                "detalle": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
