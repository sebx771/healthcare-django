from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response

from authentication.permissions import IsAdministrador, IsMedico
from ..models import Paciente
from ..serializers import PacienteSerializer
from ..services import RevisionService
from analytics.services import AnalyticsService


class PacienteUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador | IsMedico]

    def patch(self, request, pk):
        try:
            paciente = Paciente.objects.get(pk=pk)
        except Paciente.DoesNotExist:
            return Response({'error': 'Paciente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = PacienteSerializer(paciente, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        paciente.sync_flags()

        AnalyticsService.invalidar_cache_analitica()

        return Response({
            'estado': 'EXITOSO',
            'datos': serializer.data,
            'revisado': RevisionService.esta_revisado(pk),
            'revision_info': RevisionService.obtener_info_revision(pk),
        }, status=status.HTTP_200_OK)


class PacienteRevisarYActualizarView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador | IsMedico]

    def post(self, request, pk):
        try:
            paciente = Paciente.objects.get(pk=pk)
        except Paciente.DoesNotExist:
            return Response({'error': 'Paciente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        patch_data = request.data.get('patch', None)
        if patch_data is None or not isinstance(patch_data, dict):
            return Response({'error': "Se requiere campo 'patch' como objeto."}, status=status.HTTP_400_BAD_REQUEST)

        marcar_revisado = request.data.get('marcar_revisado', True)
        if marcar_revisado not in (True, False):
            return Response({'error': "'marcar_revisado' debe ser boolean."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PacienteSerializer(paciente, data=patch_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        paciente.sync_flags()

        if marcar_revisado:
            RevisionService.marcar_revisado(pk, request.user.pk, request.user.username)
        else:
            RevisionService.marcar_no_revisado(pk)

        # KPIs dependen tanto de datos como de revisión
        AnalyticsService.invalidar_cache_analitica()

        return Response({
            'estado': 'EXITOSO',
            'datos': serializer.data,
            'revisado': RevisionService.esta_revisado(pk),
            'revision_info': RevisionService.obtener_info_revision(pk),
        }, status=status.HTTP_200_OK)

