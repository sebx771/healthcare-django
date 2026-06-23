from django.core.management.base import BaseCommand
from ml.services import MLTrainerService

class Command(BaseCommand):
    help = 'Ejecuta el entrenamiento K-Fold del modelo de predicción de riesgo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--modo',
            type=str,
            default='todos',
            choices=['todos', 'solo_validos', 'ponderado'],
            help='Modo de entrenamiento: todos, solo_validos, ponderado'
        )

    def handle(self, *args, **options):
        self.stdout.write("🤖 Iniciando entrenamiento del modelo...")
        
        modo = options.get('modo', 'todos')
        exito = MLTrainerService.ejecutar_kfold_y_entrenar(modo=modo)
        
        if exito:
            self.stdout.write(self.style.SUCCESS("✅ Modelo entrenado y guardado exitosamente"))
        else:
            self.stderr.write(self.style.ERROR("❌ Fallo el entrenamiento. Revisa los logs."))