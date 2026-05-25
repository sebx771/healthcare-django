from django.db import models

class Paciente(models.Model):
    # Identificador único del CSV
    id_paciente = models.IntegerField(unique=True)
    
    # Datos Demográficos
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)
    edad = models.IntegerField()
    sexo = models.CharField(max_length=20)  # Se normalizará en el ETL (M/F)
    
    # Signos Vitales y Antropometría
    peso = models.DecimalField(max_length=5, max_digits=5, decimal_places=2)
    altura = models.DecimalField(max_length=5, max_digits=3, decimal_places=2)
    imc = models.DecimalField(max_length=5, max_digits=5, decimal_places=2, db_column='IMC')
    presion_sistolica = models.IntegerField()
    presion_diastolica = models.IntegerField()
    frecuencia_cardiaca = models.IntegerField()
    saturacion_oxigeno = models.DecimalField(max_digits=5, decimal_places=2)
    temperatura = models.DecimalField(max_digits=4, decimal_places=2)
    
    # Laboratorio
    glucosa = models.DecimalField(max_digits=6, decimal_places=2)
    colesterol = models.DecimalField(max_digits=6, decimal_places=2)
    
    # Antecedentes y Hábitos
    antecedentes_familiares = models.BooleanField(default=False)
    fumador = models.BooleanField(default=False)
    consumo_alcohol = models.BooleanField(default=False)
    actividad_fisica = models.CharField(max_length=50)
    
    # Diagnóstico y Riesgo (Campos clave para Analítica/ML)
    diagnostico_preliminar = models.CharField(max_length=150)
    riesgo_enfermedad = models.CharField(max_length=50)
    fecha_consulta = models.DateField()

    def __str__(self):
        return f"{self.nombres} {self.apellidos} - ID: {self.id_paciente}"
