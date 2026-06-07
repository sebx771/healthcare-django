from django.db import models

class Paciente(models.Model):
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)
    edad = models.IntegerField()
    sexo = models.CharField(max_length=20)
    peso = models.DecimalField(max_length=5, max_digits=5, decimal_places=2)
    altura = models.DecimalField(max_length=5, max_digits=3, decimal_places=2)
    imc = models.DecimalField(max_length=5, max_digits=5, decimal_places=2, db_column='IMC')
    presion_sistolica = models.IntegerField()
    presion_diastolica = models.IntegerField()
    frecuencia_cardiaca = models.IntegerField()
    saturacion_oxigeno = models.DecimalField(max_digits=5, decimal_places=2)
    temperatura = models.DecimalField(max_digits=4, decimal_places=2)
    glucosa = models.DecimalField(max_digits=6, decimal_places=2)
    colesterol = models.DecimalField(max_digits=6, decimal_places=2)
    antecedentes_familiares = models.BooleanField(default=False)
    fumador = models.BooleanField(default=False)
    consumo_alcohol = models.BooleanField(default=False)
    actividad_fisica = models.CharField(max_length=50)
    diagnostico_preliminar = models.CharField(max_length=150)
    riesgo_enfermedad = models.CharField(max_length=50)
    fecha_consulta = models.DateField()

    @property
    def critico(self):
       return self.presion_sistolica > 180 or self.glucosa > 300 or self.saturacion_oxigeno < 85 

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"