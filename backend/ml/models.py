from django.db import models


class MetricasModelos(models.Model):
    nombre_modelo= models.CharField(max_length=100,default="RandomForestClassifier")
    trained_at= models.DateTimeField(auto_now_add=True)

    # Metricas del modelo
    accuracy = models.FloatField(verbose_name="Accuracy (Exactitud)")
    precision = models.FloatField(verbose_name="Precision (Precisión)")
    recall = models.FloatField(verbose_name="Recall (Sensibilidad)")
    f1_score = models.FloatField(verbose_name="F1-Score")

    # Evidencia Analitica
    matriz_confusion = models.TextField(
        help_text="Matriz que cruza valores reales vs predicciones"
    )

    #  Ruta en disco del archivo binario .joblib empaquetado
    ruta_archivo_joblib = models.CharField(max_length=255)


    class Meta:
        verbose_name = "Métrica de Modelo"
        verbose_name_plural = "Métricas de Modelos"
        ordering = ['-trained_at']

    def __str__(self):
        return f"{self.nombre_modelo} - Acc: {self.accuracy:.4f} ({self.trained_at.strftime('%Y-%m-%d %H:%M')})"

