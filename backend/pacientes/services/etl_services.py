import os
import logging
import pandas as pd
from ..models import Paciente , ArchivoETL
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
            start= time()
            df_crudo = cls._extraer(ruta_archivo)
            if df_crudo is None:
                return False
            
            df_limpio = cls._transformar(df_crudo)
            registros_conteo= len(df_limpio)
            exito = cls._cargar(df_limpio)
            end = time()
            tiempo_total = end - start

            ArchivoETL.objects.create(
                    nombre=ruta_archivo,
                    registros_procesados=registros_conteo,
                    tiempo_ejecucion=tiempo_total,
                    estado='EXITOSO'
                )

            return exito
        except Exception as e:
            end = time()
            ArchivoETL.objects.create(
                nombre=ruta_archivo,
                registros_procesados=0,
                tiempo_ejecucion=end - start,
                estado='FALLIDO'
            )
            raise e


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
        df_limpio = cls._sub_calcular_imc_faltante(df_limpio)
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
    def _sub_calcular_imc_faltante(df):
        df_out = df.copy()
        if 'imc' in df_out.columns:
            mask_imc_vacio = df_out['imc'].isnull() | (df_out['imc'] == 0)
            if mask_imc_vacio.any() and 'peso' in df_out.columns and 'altura' in df_out.columns:
                pacientes_con_imc_vacio = mask_imc_vacio.sum()
                df_out.loc[mask_imc_vacio, 'imc'] = (
                    df_out.loc[mask_imc_vacio, 'peso'] / 
                    (df_out.loc[mask_imc_vacio, 'altura'] ** 2)
                )
                logger.info(f"📐 IMC calculado para {pacientes_con_imc_vacio} registros usando fórmula peso/altura².")
        return df_out

    @staticmethod
    def _sub_normalizar_datos(df):
        df_out = df.copy()

        # Diagnósticos
        if 'diagnostico_preliminar' in df_out.columns:
            df_out['diagnostico_preliminar'] = df_out['diagnostico_preliminar'].astype(str).str.strip().str.lower()
            mapeo = {
                'hipertencion': 'Hipertensión', 'hipertensíon': 'Hipertensión', 'hipertension': 'Hipertensión',
                'cardiopatia': 'Cardiopatía', 'cardiopatía': 'Cardiopatía',
                'obesidad': 'Obesidad', 'paciente sano': 'Paciente Sano', 'sano': 'Paciente Sano'
            }
            df_out['diagnostico_preliminar'] = df_out['diagnostico_preliminar'].map(mapeo).fillna(df_out['diagnostico_preliminar'].str.capitalize())

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
                es_critico = (
                    fila['presion_sistolica'] > 140 or
                    fila['presion_diastolica'] > 90 or
                    fila['saturacion_oxigeno'] < 90
                )
                if es_critico:
                    criticos_detectados += 1

                nombres_val = str(fila.get('nombres', fila.get('nombre', f"Paciente {fila['id_paciente']}")))[:150]
                apellidos_val = str(fila.get('apellidos', ''))[:150]

                paciente = Paciente(
                    id_paciente=int(fila['id_paciente']),
                    nombres=nombres_val,
                    apellidos=apellidos_val,
                    edad=int(fila['edad']),
                    sexo=str(fila['sexo']),
                    peso=fila.get('peso'),
                    altura=fila.get('altura'),
                    imc=float(fila['imc']) if pd.notna(fila.get('imc')) else None,
                    presion_sistolica=int(fila['presion_sistolica']),
                    presion_diastolica=int(fila['presion_diastolica']),
                    frecuencia_cardiaca=int(fila['frecuencia_cardiaca']),
                    saturacion_oxigeno=float(fila['saturacion_oxigeno']),
                    temperatura=fila.get('temperatura'),
                    glucosa=float(fila['glucosa']),
                    colesterol=fila.get('colesterol'),
                    antecedentes_familiares=bool(fila.get('antecedentes_familiares', False)),
                    fumador=bool(fila.get('fumador', False)),
                    consumo_alcohol=bool(fila.get('consumo_alcohol', False)),
                    actividad_fisica=str(fila.get('actividad_fisica', ''))[:50],
                    diagnostico_preliminar=str(fila.get('diagnostico_preliminar', fila.get('diagnostico', '')))[:150],
                    riesgo_enfermedad=str(fila.get('riesgo_enfermedad', ''))[:50],
                    fecha_consulta=fila.get('fecha_consulta')
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