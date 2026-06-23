from django.core.management.base import BaseCommand

from pacientes.models import Paciente
from analytics.services import AnalyticsService


class Command(BaseCommand):
    help = "Recalcula y persiste flags de riesgo para todos los Paciente."

    def handle(self, *args, **options):
        qs = Paciente.objects.all().only(
            'id',
            'riesgo_enfermedad',
            'presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca', 'saturacion_oxigeno',
            'glucosa', 'temperatura',
            'imc', 'altura', 'peso',
        )

        total = qs.count()
        hechos = 0

        for p in qs.iterator():
            p.sync_flags()
            hechos += 1

        AnalyticsService.invalidar_cache_analitica()
        self.stdout.write(self.style.SUCCESS(f"OK: recalculados {hechos}/{total} pacientes"))

