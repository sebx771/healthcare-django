import os
import pandas as pd
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ArchivoETL, Paciente

class UsuarioSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class ArchivoETLSerializer(serializers.ModelSerializer):
    usuario = UsuarioSimpleSerializer(read_only=True)
    fecha_formateada = serializers.SerializerMethodField()

    class Meta:
        model = ArchivoETL
        fields = [
            'id', 'nombre', 'loaded_at', 'fecha_formateada',
            'registros_procesados', 'tiempo_ejecucion', 'estado', 'usuario'
        ]

    def get_fecha_formateada(self, obj):
        return obj.loaded_at.strftime('%Y-%m-%d %H:%M:%S') if obj.loaded_at else None


class UploadArchivoSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        # 1. Validar extensión
        nombre_archivo = value.name
        ext = os.path.splitext(nombre_archivo)[1].lower()
        if ext not in ['.csv', '.xlsx', '.xls']:
            raise serializers.ValidationError("Formato de archivo no soportado. Debe ser .csv, .xlsx o .xls")

        # 2. Validar lectura del archivo y columnas requeridas
        try:
            # Leer una muestra o el archivo completo para validar esquema
            # Usamos read_csv/read_excel con nrows para que sea súper rápido si el archivo es enorme
            if ext == '.csv':
                df = pd.read_csv(value, nrows=5)
            else:
                df = pd.read_excel(value, engine='openpyxl', nrows=5)
        except Exception as e:
            raise serializers.ValidationError(f"No se pudo leer el archivo: {str(e)}")

        if df.empty:
            raise serializers.ValidationError("El archivo está vacío.")

        # Estandarizar nombres de columnas para la validación
        columnas = [
            str(col).strip().lower()
            .replace(' ', '_')
            .replace('ó', 'o')
            .replace('í', 'i')
            .replace('á', 'a')
            .replace('é', 'e')
            .replace('ú', 'u')
            for col in df.columns
        ]

        # Validamos columnas mínimas críticas (datos demográficos + signos vitales obligatorios)
        columnas_criticas = [
            'id_paciente', 'nombres', 'apellidos', 'edad', 'sexo',
            'presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca',
            'saturacion_oxigeno', 'glucosa', 'temperatura'
        ]
        missing_cols = [col for col in columnas_criticas if col not in columnas]
        
        if missing_cols:
            raise serializers.ValidationError(
                f"El archivo no tiene el formato o columnas requeridas por el ETL. Faltan: {', '.join(missing_cols)}"
            )

        # Regresamos el cursor del archivo al principio para que pueda volver a ser leído por el ETL
        value.seek(0)
        return value


class PacienteSerializer(serializers.ModelSerializer):
    critico = serializers.ReadOnlyField()

    class Meta:
        model = Paciente
        fields = '__all__'
