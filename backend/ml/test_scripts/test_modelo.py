# Carga rápida del modelo para verificar consistencia clínica
import os
import sys
import joblib
import pandas as pd
from django.conf import settings
import django

directorio_actual = os.path.dirname(os.path.abspath(__file__))

ruta_raiz_backend = os.path.abspath(os.path.join(directorio_actual, '..', '..'))

# 3. Inyectar esa raíz en el sistema de búsqueda de Python
sys.path.append(ruta_raiz_backend)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# 1. Buscamos el ultimo modelo guardado en la db
from ml.models import MetricasModelos
ultimo_modelo = MetricasModelos.objects.order_by('-id').first()

print(f"📦 Cargando versión inmutable: {ultimo_modelo.nombre_modelo}")
model = joblib.load(ultimo_modelo.ruta_archivo_joblib)

# 2. Definir dos pacientes fantasma (Uno muy sano y uno en crisis total)
columnas = [
    'edad', 'sexo', 'peso', 'altura', 'imc', 
    'presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca', 
    'glucosa', 'colesterol', 'saturacion_oxigeno', 'temperatura',
    'antecedentes_familiares', 'fumador', 'consumo_alcohol'
]


paciente_sano = [[30, 1, 70.0, 1.75, 22.8, 115, 75, 70, 85.0, 170.0, 98.0, 36.5, 0, 0, 0]]
paciente_critico = [[68, 0, 95.0, 1.60, 37.1, 185, 105, 95, 260.0, 290.0, 82.0, 38.2, 1, 1, 1]]

df_sano = pd.DataFrame(paciente_sano, columns=columnas)
df_critico = pd.DataFrame(paciente_critico, columns=columnas)

mapeo_inverso = {0: 'Bajo', 1: 'Medio', 2: 'Alto', 3: 'Crítico'}

pred_sano_num = model.predict(df_sano)[0]
pred_critico_num = model.predict(df_critico)[0]

print("\n====================================================")
print("🩺 RESULTADO FINAL DE LA VALIDACIÓN ANTIOVERFITTING")
print("====================================================")
print(f"🟢 Paciente Sano    -> Código: {pred_sano_num} | Diagnóstico: {mapeo_inverso.get(pred_sano_num, 'Desconocido')}")
print(f"🔴 Paciente Crítico -> Código: {pred_critico_num} | Diagnóstico: {mapeo_inverso.get(pred_critico_num, 'Desconocido')}")
print("====================================================")