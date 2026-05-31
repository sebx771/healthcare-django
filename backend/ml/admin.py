from django.contrib import admin

# backend/ml/admin.py
from django.contrib import admin
from .models import MetricasModelos

@admin.register(MetricasModelos)
class MetricasModelosAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_modelo','default','accuracy','trained_at', 'f1_score', 'ver_archivo_joblib')
    list_filter = ('trained_at','default')
    search_fields = ('nombre_modelo', 'ruta_archivo_joblib')

    ordering = ('-id',)
    

    fieldsets = (
        ('Información General del Experimento', {
            'fields': ('nombre_modelo',)
        }),
        ('Métricas de Rendimiento (Validadas vía K-Fold)', {
            'fields': (('accuracy', 'precision'), ('recall', 'f1_score'))
        }),
        ('Evidencia de Entrenamiento y Diagnóstico', {
            'fields': ('matriz_confusion', 'ruta_archivo_joblib')
        }),
    )

    readonly_fields = ('nombre_modelo', 'accuracy', 'precision', 'recall', 'f1_score', 'matriz_confusion', 'ruta_archivo_joblib')
    list_editable = ('default',)
    def ver_archivo_joblib(self, obj):
        """Muestra solo el nombre del archivo en la lista para no saturar la pantalla con la ruta completa"""
        import os
        if obj.ruta_archivo_joblib:
            return os.path.basename(obj.ruta_archivo_joblib)
        return "No asignado"
    
    # Cambia el encabezado de la columna personalizada
    ver_archivo_joblib.short_description = 'Archivo Binario (Inmutable)'
