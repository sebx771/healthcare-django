from django.contrib import admin
from .models import Paciente , ArchivoETL

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'edad', 'sexo', 'diagnostico_preliminar', 'riesgo_enfermedad')
    search_fields = ('nombres', 'apellidos')
    list_filter = ('sexo', 'riesgo_enfermedad', 'actividad_fisica')

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
