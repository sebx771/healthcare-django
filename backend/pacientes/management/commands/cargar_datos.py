import os
from django.core.management.base import BaseCommand
from django.conf import settings
from pacientes.services import ETLService

class Command(BaseCommand):
    help = 'Ejecuta el pipeline ETL buscando un archivo específico en la carpeta datasets/'

    def add_arguments(self, parser):
        # Añadimos el argumento posicional (obligatorio)
        parser.add_argument(
            'nombre_archivo', 
            type=str, 
            help='Nombre del archivo con su extensión (ej: datos.csv o datos.xlsx)'
        )

    def handle(self, *args, **options):
        
        nombre_archivo = options['nombre_archivo']
     
        ruta_datasets = os.path.join(settings.BASE_DIR, '..', 'datasets')
        ruta_final_archivo = os.path.join(ruta_datasets, nombre_archivo)
        
        
        exito = ETLService.ejecutar_pipeline(ruta_final_archivo)
        
        if exito:
            self.stdout.write(self.style.SUCCESS(f"¡ETL para '{nombre_archivo}' finalizado con éxito!"))
        else:
            self.stderr.write(f"El proceso falló. Revisa el log en backend/logs/etl.log")