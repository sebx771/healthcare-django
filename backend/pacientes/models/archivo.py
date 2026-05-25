from django.db import models
from django.contrib.auth.models import User # Por si deseas asociar el usuario más adelante

class ArchivoETL(models.Model):
    ESTADOS_CHOICES = [
        ('EXITOSO', 'Exitoso'),
        ('FALLIDO', 'Fallido'),
    ]

    nombre = models.CharField(max_length=255) 
    loaded_at = models.DateTimeField(auto_now_add=True) 
    registros_procesados = models.IntegerField(default=0)
    tiempo_ejecucion = models.FloatField(help_text="Tiempo en segundos", default=0.0) # Exigido por el reto
    estado = models.CharField(max_length=10, choices=ESTADOS_CHOICES, default='EXITOSO') # Exigido por el reto
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True) # Opcional: tracking de quién lo corrió

    class Meta:
        verbose_name = "Historial ETL"
        verbose_name_plural = "Historiales ETL"
        ordering = ['-loaded_at']

    def __str__(self):
        return f"{self.nombre} - {self.estado} ({self.loaded_at.strftime('%Y-%m-%d %H:%M')})"