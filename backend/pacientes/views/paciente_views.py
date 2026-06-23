from django.db.models import Q
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.permissions import IsAdministrador, IsMedico
from ..models import Paciente
from ..serializers import PacienteSerializer
from ..services import RevisionService


class PacientesPagination(PageNumberPagination):
    page_size = 100


class PacienteListAPIView(generics.ListAPIView):
    serializer_class = PacienteSerializer
    permission_classes = [IsAuthenticated, IsAdministrador | IsMedico]
    pagination_class = PacientesPagination

    def get_queryset(self):
        queryset = Paciente.objects.all()
        search_query = self.request.query_params.get('search', None)
        riesgo_query = self.request.query_params.get('riesgo', None)
        revisado_query = self.request.query_params.get('revisado', None)

        if search_query:
            queryset = queryset.filter(
                Q(nombres__icontains=search_query) |
                Q(apellidos__icontains=search_query)
            )

        if riesgo_query:
            if riesgo_query in ('__inconsistentes__', '__imposibles__'):
                if riesgo_query == '__inconsistentes__':
                    queryset = queryset.filter(riesgo_inconsistente_flag=True)
                else:
                    queryset = queryset.filter(critico_flag=True)
            else:
                queryset = queryset.filter(riesgo_enfermedad__iexact=riesgo_query)

        if revisado_query is not None:
            ids_revisados = RevisionService.obtener_ids_revisados()
            if revisado_query.lower() in ('1', 'true', 'si'):
                queryset = queryset.filter(pk__in=ids_revisados)
            elif revisado_query.lower() in ('0', 'false', 'no'):
                queryset = queryset.exclude(pk__in=ids_revisados)

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['ids_revisados'] = RevisionService.obtener_ids_revisados()
        return context


class PacienteDetailAPIView(generics.RetrieveAPIView):
    queryset = Paciente.objects.all()
    serializer_class = PacienteSerializer
    permission_classes = [IsAuthenticated, IsAdministrador | IsMedico]


class PacienteRevisarView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador | IsMedico]

    def post(self, request, pk):
        try:
            Paciente.objects.get(pk=pk)
        except Paciente.DoesNotExist:
            return Response({'error': 'Paciente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        RevisionService.marcar_revisado(pk, request.user.pk, request.user.username)
        return Response({
            'revisado': True,
            'revision_info': RevisionService.obtener_info_revision(pk),
        })


class PacienteNoRevisarView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador | IsMedico]

    def post(self, request, pk):
        try:
            Paciente.objects.get(pk=pk)
        except Paciente.DoesNotExist:
            return Response({'error': 'Paciente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        RevisionService.marcar_no_revisado(pk)
        return Response({'revisado': False, 'revision_info': None})
