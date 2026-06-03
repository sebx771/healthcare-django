import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .serializers import PredictSerializer
from .services.predict_services import PredictService

logger = logging.getLogger('ml_logger')

class PrediccionRiesgoAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PredictSerializer(data=request.data)
        if serializer.is_valid():
            try:
                resultado = PredictService.predecir_riesgo(serializer.validated_data)
                logger.info(f" Inferencia de API exitosa. Riesgo: {resultado}")
                return Response({
                    "estado": "EXITOSO",
                    "riesgo_predicho": resultado
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"❌ Error en inferencia: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)