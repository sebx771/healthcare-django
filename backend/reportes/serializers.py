from rest_framework import serializers
from datetime import date

class ReporteExportSerializer(serializers.Serializer):
    export_format = serializers.ChoiceField(choices=['pdf', 'excel', 'csv'], required=True)
    search = serializers.CharField(required=False, allow_blank=True)
    riesgo = serializers.CharField(required=False, allow_blank=True)
    fecha_desde = serializers.DateField(required=False)
    fecha_hasta = serializers.DateField(required=False)

    def validate(self, data):
        if data.get('fecha_desde') and data.get('fecha_hasta'):
            if data['fecha_desde'] > data['fecha_hasta']:
                raise serializers.ValidationError(
                    "La fecha 'fecha_desde' no puede ser posterior a 'fecha_hasta'."
                )
        return data