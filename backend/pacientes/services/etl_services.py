import os
import logging
import pandas as pd
from ..models import Paciente

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
        if not os.path.exists(ruta_archivo):
            logger.error(f"❌ Archivo no encontrado en: {ruta_archivo}")
            return None

        ext = os.path.splitext(ruta_archivo)[1].lower()
        
        try:
            if ext == '.csv':
                df = pd.read_csv(ruta_archivo)
            elif ext in ['.xlsx', '.xls']:
                df = pd.read_excel(ruta_archivo, engine='openpyxl')
            else:
                logger.error(f"❌ Formato de archivo no soportado: {ext}")
                return None
                
            logger.info(f"📋 Extracción exitosa ({ext}). Registros leídos: {len(df)}")
            return df
        except Exception as e:
            logger.error(f"💥 Error al leer el archivo: {str(e)}")
            return None

    @staticmethod
    def _transformar(df):
        """Fase 2: Transformación. Limpieza estricta para asegurar calidad en ML."""
        # A. Deduplicación
        filas_inicio = len(df)
        df_limpio = df.drop_duplicates(subset=['id_paciente'], keep='first').copy()
        duplicados = filas_inicio - len(df_limpio)
        if duplicados > 0:
            logger.warning(f"⚠️ Removidos {duplicados} registros duplicados.")

        
        # Si falta alguno de estos, el registro se elimina para no sesgar la IA
        constantes_vitales = ['presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca', 'saturacion_oxigeno', 'glucosa']
        
        filas_antes_vitales = len(df_limpio)
        df_limpio = df_limpio.dropna(subset=constantes_vitales).copy()
        incompletos_eliminados = filas_antes_vitales - len(df_limpio)
        
        if incompletos_eliminados > 0:
            logger.warning(f"🛡️ Seguridad ML: Se eliminaron {incompletos_eliminados} registros por falta de constantes vitales esenciales.")

        # C. Imputación Permitida (Variables no críticas para el algoritmo predictivo, como IMC o Edad si faltaran)
        columnas_secundarias = ['edad', 'imc']
        for col in columnas_secundarias:
            if col in df_limpio.columns and df_limpio[col].isnull().any():
                media = df_limpio[col].mean()
                df_limpio[col] = df_limpio[col].fillna(media)
                logger.info(f"🩹 Nulos menores en '{col}' reemplazados por la media ({media:.2f}).")

        # D. Normalizar Diagnósticos
        if 'diagnostico' in df_limpio.columns:
            df_limpio['diagnostico'] = df_limpio['diagnostico'].astype(str).str.strip().str.lower()
            mapeo = {
                'hipertencion': 'Hipertensión', 'hipertensíon': 'Hipertensión', 'hipertension': 'Hipertensión',
                'cardiopatia': 'Cardiopatía', 'cardiopatía': 'Cardiopatía',
                'obesidad': 'Obesidad', 'paciente sano': 'Paciente Sano', 'sano': 'Paciente Sano'
            }
            df_limpio['diagnostico'] = df_limpio['diagnostico'].map(mapeo).fillna(df_limpio['diagnostico'].str.capitalize())

        # E. Normalizar Sexo
        if 'sexo' in df_limpio.columns:
            df_limpio['sexo'] = df_limpio['sexo'].astype(str).str.strip().str.upper()
            df_limpio['sexo'] = df_limpio['sexo'].replace({'FEMENINO': 'F', 'MASCULINO': 'M'})
            df_limpio['sexo'] = df_limpio['sexo'].apply(lambda x: x if x in ['M', 'F'] else 'M')

        logger.info(f"✨ Transformación completada. Registros aptos para procesar: {len(df_limpio)}")
        return df_limpio

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