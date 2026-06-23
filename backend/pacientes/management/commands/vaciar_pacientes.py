from django.core.management.base import BaseCommand
from pacientes.models import Paciente


class Command(BaseCommand):
    help = "Vacía la tabla de Paciente (solo para pruebas)."

    def handle(self, *args, **options):
        qs = Paciente.objects.all()
        total = qs.count()
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f"OK: se borraron {total} pacientes."))

