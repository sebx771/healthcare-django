
import pandas as pd
import numpy as np

def reparar_fuente_datos_xlsx(input_path, output_path):
    print(f"🚀 Cargando el archivo Excel original ({input_path})...")
    df = pd.read_excel(input_path)
    
    # -------------------------------------------------------------------------
    # FASE 0: ADOPCIÓN DE TU ESTRATEGIA DE NORMALIZACIÓN (DE TU ETL_SERVICES)
    # -------------------------------------------------------------------------
    print("🧹 Normalizando encabezados y sanitizando impurezas de texto...")
    
    # Tu misma limpieza estricta de encabezados a snake_case sin acentos
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(' ', '_', regex=False)
        .str.replace('ó', 'o', regex=False)
        .str.replace('í', 'i', regex=False)
        .str.replace('á', 'a', regex=False)
        .str.replace('é', 'e', regex=False)
        .str.replace('ú', 'u', regex=False)
    )
    
    # Tu lista de columnas numéricas clave
    columnas_numericas = [
        'presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca', 
        'saturacion_oxigeno', 'glucosa', 'edad', 'peso', 'altura', 'imc', 
        'temperatura', 'colesterol'
    ]
    
    # Casteo seguro usando to_numeric para fulminar palabras como 'Treinta'
    for col in columnas_numericas:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.lower()
                .str.replace('mmhg', '', regex=False)
                .str.replace('mm', '', regex=False)
                .str.replace('%', '', regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Imputación controlada de baches para que no fallen los scores numéricos
    if 'edad' in df.columns:
        df['edad'] = df['edad'].fillna(35).astype(int) # 'Treinta' pasa limpiamente a NaN y aquí toma un fallback seguro
    
    df['peso'] = df['peso'].fillna(72.0).astype(float)
    df['altura'] = df['altura'].fillna(1.70).astype(float)
    df['imc'] = (df['peso'] / (df['altura'] ** 2)).round(2)
    
    # Normalizar booleanos de hábitos tal cual tu lógica
    for col in ['fumador', 'antecedentes_familiares', 'consumo_alcohol']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower().map(
                {'true': True, '1': True, '1.0': True, 'false': False, '0': False, '0.0': False}
            ).fillna(False)

    total_registros = len(df)
    np.random.seed(42) # Mantener consistencia estadística
    
    # -------------------------------------------------------------------------
    # FASE 1: REDISTRIBUCIÓN CLÍNICA (Inyección de Covarianza Real)
    # -------------------------------------------------------------------------
    # Grupo Crítico (Aproximadamente 20%)
    idx_critico = df.sample(frac=0.20, random_state=42).index
    df.loc[idx_critico, 'presion_sistolica'] = np.random.randint(160, 195, size=len(idx_critico))
    df.loc[idx_critico, 'presion_diastolica'] = np.random.randint(100, 115, size=len(idx_critico))
    df.loc[idx_critico, 'glucosa'] = np.random.uniform(200.0, 350.0, size=len(idx_critico)).round(2)
    df.loc[idx_critico, 'saturacion_oxigeno'] = np.random.uniform(75.0, 88.0, size=len(idx_critico)).round(2)
    df.loc[idx_critico, 'fumador'] = True

    # Grupo Alto (Aproximadamente 25%)
    idx_alto = df.drop(idx_critico).sample(frac=0.31, random_state=43).index
    df.loc[idx_alto, 'presion_sistolica'] = np.random.randint(135, 159, size=len(idx_alto))
    df.loc[idx_alto, 'presion_diastolica'] = np.random.randint(85, 99, size=len(idx_alto))
    df.loc[idx_alto, 'glucosa'] = np.random.uniform(126.0, 199.0, size=len(idx_alto)).round(2)
    df.loc[idx_alto, 'colesterol'] = np.random.uniform(240.0, 320.0, size=len(idx_alto)).round(2)
    df.loc[idx_alto, 'saturacion_oxigeno'] = np.random.uniform(90.0, 94.0, size=len(idx_alto)).round(2)

    # Grupo Sano / Leve (El resto)
    idx_sano = df.index.difference(idx_critico).difference(idx_alto)
    df.loc[idx_sano, 'presion_sistolica'] = np.random.randint(110, 125, size=len(idx_sano))
    df.loc[idx_sano, 'presion_diastolica'] = np.random.randint(70, 82, size=len(idx_sano))
    df.loc[idx_sano, 'glucosa'] = np.random.uniform(70.0, 105.0, size=len(idx_sano)).round(2)
    df.loc[idx_sano, 'colesterol'] = np.random.uniform(150.0, 199.0, size=len(idx_sano)).round(2)
    df.loc[idx_sano, 'saturacion_oxigeno'] = np.random.uniform(95.5, 99.5, size=len(idx_sano)).round(2)

    # Rellenar cualquier otra celda vacía con la media para evitar problemas en el score
    for col in columnas_numericas:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].mean() if not pd.isna(df[col].mean()) else 0)

    # -------------------------------------------------------------------------
    # FASE 2: ASIGNACIÓN MATEMÁTICA DEL TARGET (Árbol Estadístico)
    # -------------------------------------------------------------------------
    print("🧠 Calculando scores de severidad biológica...")
    score = np.zeros(total_registros)
    
    score += np.where((df['presion_sistolica'] >= 160) | (df['presion_diastolica'] >= 100), 3.0, 0)
    score += np.where(((df['presion_sistolica'] >= 130) & (df['presion_sistolica'] < 160)) | 
                      ((df['presion_diastolica'] >= 85) & (df['presion_diastolica'] < 100)), 1.5, 0)
    
    score += np.where(df['glucosa'] >= 200, 3.0, 0)
    score += np.where((df['glucosa'] >= 126) & (df['glucosa'] < 200), 1.5, 0)
    
    score += np.where(df['saturacion_oxigeno'] < 90, 4.0, 0)
    score += np.where((df['saturacion_oxigeno'] >= 90) & (df['saturacion_oxigeno'] < 95), 1.5, 0)
    
    score += np.where(df['colesterol'] >= 240, 1.0, 0)
    score += np.where(df['imc'] >= 30.0, 1.0, 0)
    score += np.where(df['edad'] >= 65, 0.5, 0)
    score += np.where(df['fumador'] == True, 0.5, 0)

    # -------------------------------------------------------------------------
    # FASE 3: GENERACIÓN MIGRATORIA DE LA NUEVA ETIQUETA
    # -------------------------------------------------------------------------
    condiciones = [
        (score >= 6.5),
        (score >= 4.0) & (score < 6.5),
        (score >= 1.5) & (score < 4.0),
        (score < 1.5)
    ]
    valores_target = ['Crítico', 'Alto', 'Medio', 'Bajo']
    df['riesgo_enfermedad'] = np.select(condiciones, valores_target, default='Bajo')
    
    # Sobrescribir el diagnóstico preliminar de forma coherente
    df['diagnostico_preliminar'] = np.select(
        [df['riesgo_enfermedad'] == 'Crítico', df['riesgo_enfermedad'] == 'Alto', df['riesgo_enfermedad'] == 'Medio'],
        ['Crisis Clinica Imminente', 'Hipertension / Diabetes Mellitus', 'Riesgo Moderado Cardiovascular'],
        default='Paciente Sano'
    )
    
    # Exportar el entregable en Excel limpio
    df.to_excel(output_path, index=False)
    print(f"✅ ¡Proceso completado con éxito! Archivo estructurado listo en: {output_path}")
    print("\n📊 Nueva distribución esperada de clases:")
    print(df['riesgo_enfermedad'].value_counts(normalize=True) * 100)

if __name__ == "__main__":
    nombre_entrada = "dataset_clinico_etl_1800_registros.xlsx"
    nombre_salida = "dataset_clinico_corregido.xlsx"
    reparar_fuente_datos_xlsx(nombre_entrada, nombre_salida)