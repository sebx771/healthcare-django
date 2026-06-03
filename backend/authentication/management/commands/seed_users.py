from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from authentication.models import Perfil

class Command(BaseCommand):
    help = 'Crea usuarios de prueba con roles específicos para el sistema (Administrador, Médico, Analista)'

    def handle(self, *args, **options):
        users_data = [
            {
                'username': 'admin_test',
                'email': 'admin@healthanalytics.com',
                'password': 'adminpassword123',
                'rol': 'Administrador',
                'is_staff': True,
                'is_superuser': True
            },
            {
                'username': 'medico_test',
                'email': 'medico@healthanalytics.com',
                'password': 'medicopassword123',
                'rol': 'Médico',
                'is_staff': False,
                'is_superuser': False
            },
            {
                'username': 'analista_test',
                'email': 'analista@healthanalytics.com',
                'password': 'analistapassword123',
                'rol': 'Analista',
                'is_staff': False,
                'is_superuser': False
            }
        ]

        for u_data in users_data:
            user, created = User.objects.get_or_create(
                username=u_data['username'],
                defaults={
                    'email': u_data['email'],
                    'is_staff': u_data['is_staff'],
                    'is_superuser': u_data['is_superuser']
                }
            )
            if created:
                user.set_password(u_data['password'])
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Usuario {user.username} creado."))
            else:
                self.stdout.write(self.style.WARNING(f"Usuario {user.username} ya existía."))

            # Crear o actualizar Perfil
            perfil, p_created = Perfil.objects.get_or_create(
                user=user,
                defaults={'rol': u_data['rol']}
            )
            if not p_created and perfil.rol != u_data['rol']:
                perfil.rol = u_data['rol']
                perfil.save()
                self.stdout.write(self.style.SUCCESS(f"Rol del perfil de {user.username} actualizado a {u_data['rol']}."))
            elif p_created:
                self.stdout.write(self.style.SUCCESS(f"Perfil de {user.username} creado con rol {u_data['rol']}."))
