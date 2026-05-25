from django.contrib import admin
from .models import Paciente

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('id_paciente', 'nombres', 'apellidos', 'edad', 'sexo', 'diagnostico_preliminar', 'riesgo_enfermedad')
    search_fields = ('nombres', 'apellidos', 'id_paciente')
    list_filter = ('sexo', 'riesgo_enfermedad', 'actividad_fisica')
