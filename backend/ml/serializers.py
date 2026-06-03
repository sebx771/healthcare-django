from rest_framework import serializers

class PredictSerializer(serializers.Serializer):
     # demograficos y Antropometricos
    edad = serializers.IntegerField(min_value=0, max_value=120)
    sexo = serializers.ChoiceField(choices=['M', 'F'])
    peso = serializers.FloatField(min_value=1.0, max_value=500.0)
    altura = serializers.FloatField(min_value=0.3, max_value=2.5)

    # datos vitales
    presion_sistolica = serializers.IntegerField(min_value=40, max_value=300)
    presion_diastolica = serializers.IntegerField(min_value=30, max_value=200)
    frecuencia_cardiaca = serializers.IntegerField(min_value=20, max_value=250)
    saturacion_oxigeno = serializers.FloatField(min_value=10.0, max_value=100.0)
    temperatura = serializers.FloatField(min_value=15.0, max_value=45.0)
    glucosa = serializers.FloatField(min_value=20.0, max_value=600.0)
    colesterol = serializers.FloatField(min_value=50.0, max_value=500.0)
    antecedentes_familiares = serializers.BooleanField()
    actividad_fisica= serializers.CharField(max_length=50)

    #  Hábitos y Conductas 
    fumador = serializers.BooleanField()
    consumo_alcohol = serializers.BooleanField()