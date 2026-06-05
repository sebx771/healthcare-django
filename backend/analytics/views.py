from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from authentication.permissions import IsAdministrador, IsMedico, IsAnalista
from .services import AnalyticsService

class DashboardKPIsAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador | IsMedico | IsAnalista]

    def get(self, request, *args, **kwargs):
        try:
            # Consumimos el servicio que lee directo de Redis (o calcula con Pandas si es un Cache Miss)
            data = AnalyticsService.obtener_kpis_descriptivos()
            
            return Response({
                "estado": "EXITOSO",
                "datos": data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "estado": "ERROR",
                "detalle": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
