import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

from authentication.permissions import IsAdministrador, IsAnalista
from ..models import ArchivoETL
from ..serializers import ArchivoETLSerializer, UploadArchivoSerializer
from ..services import ETLService

class ETLRunView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador | IsAnalista]

    def post(self, request, *args, **kwargs):
        nombre_archivo = request.data.get('archivo', 'dataset_clinico_corregido.xlsx')
        
        try:
            exito = ETLService.ejecutar_pipeline(nombre_archivo, usuario=request.user)
            if exito:
                return Response({
                    "status": "success",
                    "message": f"El pipeline ETL para '{nombre_archivo}' se ejecutó correctamente."
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "failed",
                    "message": f"El pipeline ETL para '{nombre_archivo}' falló. Revise los logs."
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Ocurrió un error al ejecutar el ETL: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PacientesUploadView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador | IsAnalista]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        serializer = UploadArchivoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data['file']
        
        # Generar nombre único para evitar colisiones
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_guardado = f"upload_{timestamp}_{uploaded_file.name}"
        
        # Guardar en la carpeta datasets/
        ruta_datasets = os.path.abspath(os.path.join(settings.BASE_DIR, '..', 'datasets'))
        os.makedirs(ruta_datasets, exist_ok=True)
        
        fs = FileSystemStorage(location=ruta_datasets)
        filename = fs.save(nombre_guardado, uploaded_file)
        ruta_completa = fs.path(filename)

        try:
            exito = ETLService.ejecutar_pipeline(ruta_completa, usuario=request.user)
            if exito:
                # Obtener el registro creado recientemente para retornar detalles
                ultimo_historial = ArchivoETL.objects.filter(nombre=nombre_guardado).first()
                datos_historial = ArchivoETLSerializer(ultimo_historial).data if ultimo_historial else None
                
                return Response({
                    "status": "success",
                    "message": "Archivo cargado y procesado exitosamente por el ETL.",
                    "details": datos_historial
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "status": "failed",
                    "message": "La carga del archivo falló al procesarse en el pipeline ETL. Revise los logs."
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Ocurrió un error al procesar el archivo subido: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ETLHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdministrador | IsAnalista]
    queryset = ArchivoETL.objects.all().order_by('-loaded_at')
    serializer_class = ArchivoETLSerializer
