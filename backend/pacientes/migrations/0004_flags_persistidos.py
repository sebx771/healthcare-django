from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pacientes', '0003_remove_paciente_id_paciente'),
    ]

    operations = [
        migrations.AddField(
            model_name='paciente',
            name='critico_flag',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='paciente',
            name='sospechoso_flag',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='paciente',
            name='riesgo_inconsistente_flag',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='paciente',
            name='nivel_riesgo_calculado_persistido',
            field=models.CharField(default='Bajo', max_length=50),
        ),
    ]

