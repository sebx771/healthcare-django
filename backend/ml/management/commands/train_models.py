from django.core.management.base import BaseCommand
from ml.services import MLTrainerService

class Command(BaseCommand):
    help = 'Ejecuta el entrenamiento K-Fold del modelo de predicción de riesgo'

    def handle(self, *args, **options):
        self.stdout.write("🤖 Iniciando entrenamiento del modelo...")
        
        exito = MLTrainerService.ejecutar_kfold_y_entrenar()
        
        if exito:
            self.stdout.write(self.style.SUCCESS("✅ Modelo entrenado y guardado exitosamente"))
        else:
            self.stderr.write(self.style.ERROR("❌ Fallo el entrenamiento. Revisa los logs."))