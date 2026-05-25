import os
import logging
import pandas as pd
from ..models import Paciente
from django.conf import settings

logger = logging.getLogger('etl_logger')

class ETLService:

    @classmethod
    def ejecutar_pipeline(cls, ruta_archivo):
        logger.info("==================================================")
        logger.info("🚀 INICIANDO PROCESO ETL - PIPELINE INTEGRADO")
        logger.info("==================================================")

        df_crudo = cls._extraer(ruta_archivo)
        if df_crudo is None:
            return False

        df_limpio = cls._transformar(df_crudo)
        exito = cls._cargar(df_limpio)
        return exito

    @staticmethod
    def _extraer(ruta_archivo):
        ruta_completa = os.path.abspath(os.path.join(settings.BASE_DIR, '..', 'datasets', ruta_archivo))
        if not os.path.exists(f'{ruta_completa}'):
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
        """Fase 2: Transformación modularizada."""
        df_limpio = cls._sub_deduplicar(df)
        df_limpio = cls._sub_limpiar_nulos_criticos(df_limpio)
        df_limpio = cls._sub_validar_rangos_clinicos(df_limpio)
        df_limpio = cls._sub_imputar_permitidos(df_limpio)
        df_limpio = cls._sub_normalizar_datos(df_limpio)
        
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
    def _sub_limpiar_nulos_criticos(df):
        constantes = ['presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca', 'saturacion_oxigeno', 'glucosa']
        filas_inicio = len(df)
        df_out = df.dropna(subset=constantes).copy()
        eliminados = filas_inicio - len(df_out)
        if eliminados > 0:
            logger.warning(f"🛡️ Seguridad ML: Se eliminaron {eliminados} registros por nulos vitales.")
        return df_out

    @staticmethod
    def _sub_validar_rangos_clinicos(df):
        filas_inicio = len(df)
        df_out = df[
            (df['presion_sistolica'] >= 40) & (df['presion_sistolica'] <= 300) &
            (df['presion_diastolica'] >= 30) & (df['presion_diastolica'] <= 200) &
            (df['saturacion_oxigeno'] >= 10) & (df['saturacion_oxigeno'] <= 100) &
            (df['frecuencia_cardiaca'] >= 20) & (df['frecuencia_cardiaca'] <= 250) &
            (df['glucosa'] >= 20) & (df['glucosa'] <= 600)
        ].copy()
        erroneos = filas_inicio - len(df_out)
        if erroneos > 0:
            logger.error(f"❌ CONTROL MÉDICO: Se descartaron {erroneos} registros con valores biológicamente imposibles.")
        return df_out

    @staticmethod
    def _sub_imputar_permitidos(df):
        df_out = df.copy()
        for col in ['edad', 'imc']:
            if col in df_out.columns and df_out[col].isnull().any():
                media = df_out[col].mean()
                df_out[col] = df_out[col].fillna(media)
                logger.info(f"🩹 Nulos menores en '{col}' reemplazados por la media ({media:.2f}).")
        return df_out

    @staticmethod
    def _sub_normalizar_datos(df):
        df_out = df.copy()
        
        # Diagnósticos
        if 'diagnostico' in df_out.columns:
            df_out['diagnostico'] = df_out['diagnostico'].astype(str).str.strip().str.lower()
            mapeo = {
                'hipertencion': 'Hipertensión', 'hipertensíon': 'Hipertensión', 'hipertension': 'Hipertensión',
                'cardiopatia': 'Cardiopatía', 'cardiopatía': 'Cardiopatía',
                'obesidad': 'Obesidad', 'paciente sano': 'Paciente Sano', 'sano': 'Paciente Sano'
            }
            df_out['diagnostico'] = df_out['diagnostico'].map(mapeo).fillna(df_out['diagnostico'].str.capitalize())

        # Sexo
        if 'sexo' in df_out.columns:
            df_out['sexo'] = df_out['sexo'].astype(str).str.strip().str.upper()
            df_out['sexo'] = df_out['sexo'].replace({'FEMENINO': 'F', 'MASCULINO': 'M'})
            df_out['sexo'] = df_out['sexo'].apply(lambda x: x if x in ['M', 'F'] else 'M')
            
        return df_out
    @staticmethod
    def _cargar(df):
        try:
            Paciente.objects.all().delete()
            
            pacientes_a_crear = []
            criticos_detectados = 0

            for _, fila in df.iterrows():
                # Regla de negocio para alertas
                es_critico = (
                    fila['presion_sistolica'] > 140 or 
                    fila['presion_diastolica'] > 90 or 
                    fila['saturacion_oxigeno'] < 90
                )
                if es_critico:
                    criticos_detectados += 1

                paciente = Paciente(
                    id_paciente=fila['id_paciente'],
                    nombre=fila.get('nombre', f"Paciente {fila['id_paciente']}"),
                    edad=int(fila['edad']),
                    sexo=fila['sexo'],
                    presion_sistolica=float(fila['presion_sistolica']),
                    presion_diastolica=float(fila['presion_diastolica']),
                    frecuencia_cardiaca=float(fila['frecuencia_cardiaca']),
                    saturacion_oxigeno=float(fila['saturacion_oxigeno']),
                    glucosa=float(fila['glucosa']),
                    imc=float(fila['imc']),
                    diagnostico=fila['diagnostico'],
                    es_critico=es_critico
                )
                pacientes_a_crear.append(paciente)

            Paciente.objects.bulk_create(pacientes_a_crear)
            logger.info(f"✅ CARGA EXITOSA: {len(pacientes_a_crear)} registros limpios en la BD.")
            logger.info(f"🚨 Alertas críticas detectadas activas: {criticos_detectados}")
            return True
        except Exception as e:
            logger.error(f"💥 Fallo crítico en la carga a la BD: {str(e)}", exc_info=True)
            return False

if '__name__'=='__main__': 
    pass    