
import os
import sys
import django
import pandas as pd

# Configurar entorno de Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings") 
django.setup()

from pacientes.models import Paciente

def ejecutar_auditoria():
    print("="*60)
    print("🔬 SCRIPT DE AUDITORÍA CRÍTICA DE MACHINE LEARNING")
    print("="*60)
    
    queryset = Paciente.objects.all().values(
        'edad', 'sexo', 'peso', 'altura', 'imc', 
        'presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca', 
        'glucosa', 'colesterol', 'saturacion_oxigeno', 'temperatura',
        'antecedentes_familiares', 'fumador', 'consumo_alcohol',
        'riesgo_enfermedad'
    )
    
    if not queryset.exists():
        print("❌ ERROR: La base de datos está vacía.")
        return

    df = pd.DataFrame(list(queryset))
    
    # 1. Inspeccionar Distribución Real del Target
    print("\n📊 1. DISTRIBUCIÓN DE LA VARIABLE OBJETIVO (riesgo_enfermedad):")
    dist_target = df['riesgo_enfermedad'].value_counts()
    dist_porcentaje = df['riesgo_enfermedad'].value_counts(normalize=True) * 100
    for idx in dist_target.index:
        print(f"   - {idx}: {dist_target[idx]} registros ({dist_porcentaje[idx]:.2f}%)")
        
    # 2. Mapeo y verificación de Nulos Ocultos
    s_target_limpio = df['riesgo_enfermedad'].astype(str).str.strip().str.lower().str.replace('ítico', 'itico', regex=False)
    mapeo_riesgo = {'bajo': 0, 'medio': 1, 'alto': 2, 'critico': 3}
    df['target'] = s_target_limpio.map(mapeo_riesgo)
    
    nulos_target = df['target'].isna().sum()
    print(f"\n⚠️ 2. ANÁLISIS DE MAPEO:")
    print(f"   - Registros no reconocidos por el diccionario (NaN): {nulos_target}")
    if nulos_target > 0:
        print(f"   - Strings huérfanas encontradas en BD: {df[df['target'].isna()]['riesgo_enfermedad'].unique()}")

    # 3. Inspección de datos médicos (Verificar que no sean planos o idénticos)
    print("\n🧬 3. ANÁLISIS DE COMPORTAMIENTO CLÍNICO (Promedios por Riesgo):")
    df['target'] = df['target'].fillna(0).astype(int)
    
    columnas_clave = ['glucosa', 'presion_sistolica', 'saturacion_oxigeno', 'imc']
    columnas_existentes = [c for c in columnas_clave if c in df.columns]
    
    if columnas_existentes:
        # Agrupamos por target para ver si los enfermos crónicos tienen métricas distintas a los sanos
        reporte_clinico = df.groupby('riesgo_enfermedad')[columnas_existentes].mean()
        print(reporte_clinico)
    else:
        print("   - No se pudieron analizar métricas clínicas.")

    print("\n" + "="*60)

if __name__ == "__main__":
    ejecutar_auditoria()