import os
from django.core.management.base import BaseCommand
from django.conf import settings
from pacientes.services import ETLService

class Command(BaseCommand):
    help = 'Ejecuta el pipeline ETL para archivos CSV o Excel clínicos'

    def handle(self, *args, **options):
        # settings.BASE_DIR apunta a 'backend/'. Subimos un nivel ('..') para buscar el archivo.
        ruta = os.path.join(settings.BASE_DIR, '..', 'dataset_clinico.csv')
        
        # Ejecuta el servicio que orquesta la extracción, limpieza estricta de ML y carga
        exito = ETLService.ejecutar_pipeline(ruta)
        
        if exito:
            self.stdout.write(self.style.SUCCESS("¡ETL finalizado con éxito! Revisa backend/logs/etl.log"))
        else:
            self.stderr.write("El proceso ETL falló. Revisa el log en backend/logs/etl.log")