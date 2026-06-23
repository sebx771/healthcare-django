from django.contrib import admin
from django.contrib import messages
from .models import Paciente , ArchivoETL
from .services import RevisionService


class RevisadoFilter(admin.SimpleListFilter):
    title = 'Revisado'
    parameter_name = 'revisado'

    def lookups(self, request, model_admin):
        return [('si', 'Sí'), ('no', 'No')]

    def queryset(self, request, queryset):
        ids_revisados = RevisionService.obtener_ids_revisados()
        if self.value() == 'si':
            return queryset.filter(pk__in=ids_revisados)
        if self.value() == 'no':
            return queryset.exclude(pk__in=ids_revisados)
        return queryset


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = (
        'nombres',
        'apellidos',
        'edad',
        'sexo',
        'diagnostico_preliminar',
        'riesgo_enfermedad',
        'nivel_riesgo_calculado',
        'critico',
        'sospechoso',
        'riesgo_inconsistente',
        'revisado',
    )
    search_fields = ('nombres', 'apellidos')
    list_filter = ('sexo', 'riesgo_enfermedad', 'actividad_fisica', RevisadoFilter)
    actions = ['marcar_como_revisado', 'marcar_como_no_revisado']

    def critico(self, obj):
        return obj.critico

    critico.boolean = True
    critico.short_description = 'Crítico'

    def sospechoso(self, obj):
        return obj.sospechoso

    sospechoso.boolean = True
    sospechoso.short_description = 'Sospechoso'

    def riesgo_inconsistente(self, obj):
        return obj.riesgo_inconsistente

    riesgo_inconsistente.boolean = True
    riesgo_inconsistente.short_description = 'Riesgo Inconsistente'

    def nivel_riesgo_calculado(self, obj):
        return obj.nivel_riesgo_calculado

    nivel_riesgo_calculado.short_description = 'Riesgo Calculado'

    @admin.display(boolean=True, description='Revisado')
    def revisado(self, obj):
        return RevisionService.esta_revisado(obj.pk)

    @admin.action(description='Marcar como revisado')
    def marcar_como_revisado(self, request, queryset):
        for obj in queryset:
            RevisionService.marcar_revisado(obj.pk, request.user.pk, request.user.username)
        self.message_user(request, f'{queryset.count()} paciente(s) marcado(s) como revisado(s).', messages.SUCCESS)

    @admin.action(description='Marcar como no revisado')
    def marcar_como_no_revisado(self, request, queryset):
        for obj in queryset:
            RevisionService.marcar_no_revisado(obj.pk)
        self.message_user(request, f'{queryset.count()} paciente(s) marcado(s) como no revisado(s).', messages.SUCCESS)


@admin.register(ArchivoETL)
class ArchivoETLAdmin(admin.ModelAdmin):
  
    list_display = ('nombre', 'estado', 'registros_procesados', 'tiempo_ejecucion_formateado', 'loaded_at', 'usuario')
    list_filter = ('estado', 'loaded_at', 'usuario')
    search_fields = ('nombre',)
    
    # Bloqueamos la edición en el admin para que actúe estrictamente como un Log inalterable (Read Only)
    readonly_fields = ('nombre', 'loaded_at', 'registros_procesados', 'tiempo_ejecucion', 'estado', 'usuario')

    def tiempo_ejecucion_formateado(self, obj):
        """Muestra el tiempo de ejecución con dos decimales y el sufijo 'seg'"""
        return f"{obj.tiempo_ejecucion:.2f} seg"
    
    tiempo_ejecucion_formateado.short_description = 'Tiempo de Ejecución'
