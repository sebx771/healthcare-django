import os
import logging
import pandas as pd
from ..models import Paciente, ArchivoETL
from django.conf import settings
from time import time

logger = logging.getLogger('etl_logger')

class ETLService:

    @classmethod
    def ejecutar_pipeline(cls, ruta_archivo):
        logger.info("==================================================")
        logger.info("🚀 INICIANDO PROCESO ETL - PIPELINE INTEGRADO")
        logger.info("==================================================")

        try:
            start = time()
            df_crudo = cls._extraer(ruta_archivo)
            if df_crudo is None:
                return False
            
            df_limpio = cls._transformar(df_crudo)
            registros_conteo = len(df_limpio)
            exito = cls._cargar(df_limpio)
            end = time()
            tiempo_total = end - start

            ArchivoETL.objects.create(
                nombre=os.path.basename(ruta_archivo),
                registros_procesados=registros_conteo,
                tiempo_ejecucion=tiempo_total,
                estado='EXITOSO'
            )
            # limpiamos el cache de redis para actualizarlo con los nuevos datos 
            logger.info("")
            from analytics.services import AnalyticsService
            AnalyticsService.invalidar_cache_analitica()

            return exito
        except Exception as e:
            end = time()
            ArchivoETL.objects.create(
                nombre=os.path.basename(ruta_archivo),
                registros_procesados=0,
                tiempo_ejecucion=end - start,
                estado='FALLIDO'
            )
            raise e

    @staticmethod
    def _extraer(ruta_archivo):
        ruta_completa = os.path.abspath(os.path.join(settings.BASE_DIR, '..', 'datasets', ruta_archivo))
        if not os.path.exists(ruta_completa):
            logger.error(f"❌ Archivo no encontrado en: {ruta_archivo}")
            return None

        ext = os.path.splitext(ruta_archivo)[1].lower()
        
        try:
            if ext == '.csv':
                df = pd.read_csv(ruta_completa)
            elif ext in ['.xlsx', '.xls']:
                df = pd.read_excel(ruta_completa, engine='openpyxl')
            else:
                logger.error(f"❌ Formato de archivo no soportado: {ext}")
                return None
                
            logger.info(f"📋 Extracción exitosa ({ext}). Registros leídos: {len(df)}")
            return df
        except Exception as e:
            logger.error(f"💥 Error al leer el archivo: {str(e)}")
            return None

    @classmethod
    def _transformar(cls, df):
        # 1. Estandarizar nombres de columnas y limpiar cadenas de texto flotantes (mmHg, %)
        df_limpio = cls._sub_normalizar_estructuras(df)
        
        # 2. Filtrar duplicados por ID de paciente
        df_limpio = cls._sub_deduplicar(df_limpio)
        
        # 3. Aplicar política estricta de ML: Purgar si faltan signos vitales nucleares
        df_limpio = cls._sub_purgar_nulos_vitales(df_limpio)
        
        # 4. Validar consistencia biológica de rangos clínicos
        df_limpio = cls._sub_validar_rangos_clinicos(df_limpio)
        
        # 5. Imputar variables metabólicas y antropométricas faltantes (Colesterol, Peso, IMC)
        df_limpio = cls._sub_imputar_metabolicos(df_limpio)
        
        # 6. Recalcular IMC en base a datos imputados si es requerido
        df_limpio = cls._sub_calcular_imc_faltante(df_limpio)
        
        logger.info(f"✨ Transformación completada. Registros aptos: {len(df_limpio)}")
        return df_limpio

    @staticmethod
    def _sub_deduplicar(df):
        filas_inicio = len(df)
        df_out = df.drop_duplicates(subset=['id_paciente'], keep='first').copy()
        duplicados = filas_inicio - len(df_out)
        if duplicados > 0:
            logger.warning(f"⚠️ Removidos {duplicados} registros duplicados.")
        return df_out

    @staticmethod
    def _sub_normalizar_estructuras(df):
        df_out = df.copy()

        # Normalización estricta de encabezados a snake_case
        df_out.columns = (
            df_out.columns.str.strip()
            .str.lower()
            .str.replace(' ', '_', regex=False)
            .str.replace('ó', 'o', regex=False)
            .str.replace('í', 'i', regex=False)
            .str.replace('á', 'a', regex=False)
            .str.replace('é', 'e', regex=False)
            .str.replace('ú', 'u', regex=False)
        )

        # Limpieza de sufijos y conversión a tipos numéricos puros
        columnas_numericas = [
            'presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca', 
            'saturacion_oxigeno', 'glucosa', 'edad', 'peso', 'altura', 'imc', 
            'temperatura', 'colesterol'
        ]
        for col in columnas_numericas:
            if col in df_out.columns:
                df_out[col] = (
                    df_out[col].astype(str)
                    .str.lower()
                    .str.replace('mmhg', '', regex=False)
                    .str.replace('mm', '', regex=False)
                    .str.replace('%', '', regex=False)
                    .str.strip()
                )
                df_out[col] = pd.to_numeric(df_out[col], errors='coerce')

        # Normalización de variables categóricas (Diagnóstico)
        if 'diagnostico_preliminar' in df_out.columns:
            df_out['diagnostico_preliminar'] = df_out['diagnostico_preliminar'].astype(str).str.strip().str.lower()
            mapeo = {
                'hipertencion': 'Hipertensión', 'hipertensíon': 'Hipertensión', 'hipertension': 'Hipertensión',
                'cardiopatia': 'Cardiopatía', 'cardiopatía': 'Cardiopatía',
                'obesidad': 'Obesidad', 'paciente sano': 'Paciente Sano', 'sano': 'Paciente Sano'
            }
            df_out['diagnostico_preliminar'] = df_out['diagnostico_preliminar'].map(mapeo).fillna(df_out['diagnostico_preliminar'].str.capitalize())

        # Normalización de variables categóricas (Sexo)
        if 'sexo' in df_out.columns:
            df_out['sexo'] = df_out['sexo'].astype(str).str.strip().str.upper()
            df_out['sexo'] = df_out['sexo'].replace({'FEMENINO': 'F', 'MASCULINO': 'M'})
            df_out['sexo'] = df_out['sexo'].apply(lambda x: x if x in ['M', 'F'] else 'M')

        return df_out

    @staticmethod
    def _sub_purgar_nulos_vitales(df):
        # 6 Signos vitales estrictamente necesarios para que el registro tenga sentido clínico
        vitales_criticos = ['presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca', 'saturacion_oxigeno', 'glucosa', 'temperatura']
        
        filas_inicio = len(df)
        df_out = df.dropna(subset=vitales_criticos).copy()
        eliminados = filas_inicio - len(df_out)
        
        if eliminados > 0:
            logger.warning(f"🛡️ Filtro ML Seguro: Se purgaron {eliminados} registros por ausencia de signos vitales críticos.")
        return df_out

    @staticmethod
    def _sub_validar_rangos_clinicos(df):
        filas_inicio = len(df)
        df_out = df[
            (df['presion_sistolica'] >= 40) & (df['presion_sistolica'] <= 300) &
            (df['presion_diastolica'] >= 30) & (df['presion_diastolica'] <= 200) &
            (df['saturacion_oxigeno'] >= 10) & (df['saturacion_oxigeno'] <= 100) &
            (df['frecuencia_cardiaca'] >= 20) & (df['frecuencia_cardiaca'] <= 250) &
            (df['glucosa'] >= 20) & (df['glucosa'] <= 600) &
            (df['temperatura'] >= 15) & (df['temperatura'] <= 45)
        ].copy()
        
        erroneos = filas_inicio - len(df_out)
        if erroneos > 0:
            logger.error(f"❌ CONTROL MÉDICO: Se descartaron {erroneos} registros con valores biológicamente imposibles.")
        return df_out

    @staticmethod
    def _sub_imputar_metabolicos(df):
        df_out = df.copy()
        # Campos que pueden admitir imputación estadística sin sesgar críticamente el diagnóstico inmediato
        columnas_a_imputar = ['colesterol', 'peso', 'altura', 'imc', 'edad']
        
        for col in columnas_a_imputar:
            if col in df_out.columns and df_out[col].isnull().any():
                media = df_out[col].mean()
                # Si todo el dataframe estuviera vacío en esa columna por algún error, usar un fallback estándar
                if pd.isna(media):
                    media = 0.0 if col != 'edad' else 40
                df_out[col] = df_out[col].fillna(media)
                logger.info(f"🩹 Imputación ML: Nulos en '{col}' reemplazados por la media estadística ({media:.2f}).")
        return df_out

    @staticmethod
    def _sub_calcular_imc_faltante(df):
        df_out = df.copy()
        if 'imc' in df_out.columns:
            mask_imc_inconsistente = df_out['imc'].isnull() | (df_out['imc'] == 0)
            if mask_imc_inconsistente.any() and 'peso' in df_out.columns and 'altura' in df_out.columns:
                df_out.loc[mask_imc_inconsistente, 'imc'] = (
                    df_out.loc[mask_imc_inconsistente, 'peso'] / 
                    (df_out.loc[mask_imc_inconsistente, 'altura'] ** 2)
                )
        return df_out

    @staticmethod
    def _cargar(df):
        try:
            # TODO: Implementar lógica para la creación-actualización de datos del modelo pacientes
            Paciente.objects.all().delete()

            pacientes_a_crear = []
            criticos_detectados = 0

            for _, fila in df.iterrows():
                # Detección preventiva de alertas de emergencias clínicas
                es_critico = (
                    fila['presion_sistolica'] > 180 or
                    fila['presion_diastolica'] > 120 or  # Ajustado a un umbral clínico real
                    fila['saturacion_oxigeno'] < 85
                )
                if es_critico:
                    criticos_detectados += 1

                # Mapeo y saneamiento de datos administrativos/opcionales de texto
                nombres_val = str(fila.get('nombres', fila.get('nombre', f"Paciente {fila['id_paciente']}")))[:150]
                apellidos_val = str(fila.get('apellidos', 'Anonimizado'))[:150]
                
                # Reemplazo de marcas de texto para booleanos por seguridad
                def safe_bool(val):
                    if isinstance(val, bool): return val
                    return str(val).strip().lower() in ['true', '1', 'yes', 'si']

                paciente = Paciente(
                    id_paciente=int(fila['id_paciente']),
                    nombres=nombres_val,
                    apellidos=apellidos_val,
                    edad=int(fila['edad']),
                    sexo=str(fila['sexo']),
                    peso=float(fila['peso']),
                    altura=float(fila['altura']),
                    imc=float(fila['imc']),
                    presion_sistolica=int(fila['presion_sistolica']),
                    presion_diastolica=int(fila['presion_diastolica']),
                    frecuencia_cardiaca=int(fila['frecuencia_cardiaca']),
                    saturacion_oxigeno=float(fila['saturacion_oxigeno']),
                    temperatura=float(fila['temperatura']),
                    glucosa=float(fila['glucosa']),
                    colesterol=float(fila['colesterol']),
                    antecedentes_familiares=safe_bool(fila.get('antecedentes_familiares', False)),
                    fumador=safe_bool(fila.get('fumador', False)),
                    consumo_alcohol=safe_bool(fila.get('consumo_alcohol', False)),
                    actividad_fisica=str(fila.get('actividad_fisica', 'Sedentario'))[:50],
                    diagnostico_preliminar=str(fila.get('diagnostico_preliminar', 'Sin Diagnóstico'))[:150],
                    riesgo_enfermedad=str(fila.get('riesgo_enfermedad', 'Bajo'))[:50],
                    fecha_consulta=fila.get('fecha_consulta') if pd.notna(fila.get('fecha_consulta')) else None
                )
                pacientes_a_crear.append(paciente)

            Paciente.objects.bulk_create(pacientes_a_crear)
            logger.info(f"✅ CARGA EXITOSA: {len(pacientes_a_crear)} registros limpios insertados en la BD.")
            logger.info(f"🚨 Alertas críticas detectadas activas: {criticos_detectados}")
            return True
        except Exception as e:
            logger.error(f"💥 Fallo crítico en la carga a la BD: {str(e)}", exc_info=True)
            return False