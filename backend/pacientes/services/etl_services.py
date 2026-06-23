import os
import logging
from collections import defaultdict
import pandas as pd
from ..models import Paciente, ArchivoETL
from django.conf import settings
from time import time

logger = logging.getLogger('etl_logger')

class ETLService:

    @classmethod
    def ejecutar_pipeline(cls, ruta_archivo, usuario=None):
        logger.info("==================================================")
        logger.info("🚀 INICIANDO PROCESO ETL - PIPELINE INTEGRADO")
        logger.info("==================================================")

        try:
            start = time()
            df_crudo = cls._extraer(ruta_archivo)
            if df_crudo is None:
                return False

            metricas = defaultdict(int)
            df_limpio = cls._transformar(df_crudo, metricas)
            registros_conteo = len(df_limpio)
            cls._registrar_metricas(metricas)
            exito = cls._cargar(df_limpio)
            end = time()
            tiempo_total = end - start

            ArchivoETL.objects.create(
                nombre=os.path.basename(ruta_archivo),
                registros_procesados=registros_conteo,
                tiempo_ejecucion=tiempo_total,
                estado='EXITOSO',
                usuario=usuario
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
                estado='FALLIDO',
                usuario=usuario
            )
            raise e

    @staticmethod
    def _extraer(ruta_archivo):
        # primero nos aseguramos que la ruta no sea absoluta
        if os.path.isabs(ruta_archivo) and os.path.exists(ruta_archivo):
            ruta_completa = ruta_archivo
        else:
            ruta_completa = os.path.abspath(os.path.join(settings.BASE_DIR, 'datasets', ruta_archivo))

        if not os.path.exists(ruta_completa):
            logger.error(f"❌ Archivo no encontrado en: {ruta_archivo} (Ruta resuelta: {ruta_completa})")
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
    def _transformar(cls, df, metricas=None):
        metricas = metricas or defaultdict(int)

        # 1. Estandarizar nombres de columnas, limpiar unidades y mapear valores textuales clínicos ("Alta", etc.)
        df_limpio = cls._sub_normalizar_estructuras(df, metricas)

        # --- NUEVO FILTRO OBLIGATORIO DE BORRADO ---
        # Si vienen celdas vacías de verdad en campos obligatorios de identidad o vitales, la fila se elimina.
        filas_antes_limpieza = len(df_limpio)
        
        columnas_obligatorias = [
            'nombres', 'apellidos', 'edad', 
            'presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca', 
            'saturacion_oxigeno', 'glucosa', 'temperatura'
        ]
        
        # Elimina filas donde cualquiera de estas columnas sea NaN
        df_limpio = df_limpio.dropna(subset=columnas_obligatorias).copy()
        
        filas_borradas = filas_antes_limpieza - len(df_limpio)
        if filas_borradas > 0:
            metricas['registros_eliminados_por_nulos_criticos'] += filas_borradas
            logger.warning(f"🗑️ Se eliminaron {filas_borradas} registros por ausencia de datos vitales o identidad obligatorios.")
        # --------------------------------------------

        # 2. Filtrar duplicados por ID de paciente (nombres + apellidos + edad)
        df_limpio = cls._sub_deduplicar(df_limpio, metricas)

        # 3. Conservar registros con signos vitales faltantes e imputarlos (Solo aplica a columnas no obligatorias en el dropna anterior)
        df_limpio = cls._sub_imputar_nulos_vitales(df_limpio, metricas)

        # 4. Clasificar rangos clínicos y fisiológicos sin descartar registros
        df_limpio = cls._sub_clasificar_rangos(df_limpio, metricas)

        # 5. Imputar variables metabólicas y antropométricas faltantes (Colesterol, Peso, Altura) -> ¡Aquí no se borra!
        df_limpio = cls._sub_imputar_metabolicos(df_limpio, metricas)

        # 6. Recalcular IMC en base a datos de peso y altura imputados si viene vacío o en 0
        df_limpio = cls._sub_calcular_imc_faltante(df_limpio, metricas)

        logger.info(f"✨ Transformación completada. Registros conservados: {len(df_limpio)}")
        return df_limpio

    @staticmethod
    def _sub_deduplicar(df, metricas=None):
        metricas = metricas or defaultdict(int)
        filas_inicio = len(df)
        

        df_out = df.drop_duplicates(keep='first').copy()
        
        duplicados = filas_inicio - len(df_out)
        metricas['registros_duplicados'] += duplicados
        if duplicados > 0:
            logger.warning(f"⚠️ Removidos {duplicados} registros con filas 100% idénticas (duplicados exactos).")
        return df_out

    @staticmethod
    def _sub_normalizar_estructuras(df, metricas=None):
        metricas = metricas or defaultdict(int)
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
                df_out[col] = df_out[col].apply(
                    lambda valor: ETLService._mapear_valor_textual(valor, col, metricas)
                )
                df_out[col] = (
                    df_out[col].astype(str)
                    .str.lower()
                    .str.replace('mmhg', '', regex=False)
                    .str.replace('mm', '', regex=False)
                    .str.replace('%', '', regex=False)
                    .str.replace(',', '.', regex=False)
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
    def _normalizar_texto_clinico(valor):
        if pd.isna(valor):
            return None
        texto = str(valor).strip().lower()
        texto = (
            texto.replace('ó', 'o')
            .replace('í', 'i')
            .replace('á', 'a')
            .replace('é', 'e')
            .replace('ú', 'u')
            .replace(' mmhg', '')
            .replace('mmhg', '')
            .replace(' mm', '')
            .replace('%', '')
            .replace(' ', '_')
            .strip('_')
        )
        alias = {
            'alto': 'alta',
            'elevada': 'alta',
            'elevado': 'alta',
            'bajo': 'baja',
            'normalidad': 'normal',
        }
        return alias.get(texto, texto)

    @staticmethod
    def _mapear_valor_textual(valor, columna, metricas):
        mapeo = settings.CLINICAL_TEXT_VALUE_MAPPINGS.get(columna, {})
        if not mapeo:
            return valor
        texto = ETLService._normalizar_texto_clinico(valor)
        if texto in mapeo:
            metricas['textuales_mapeados'] += 1
            metricas[f'textuales_mapeados_{columna}'] += 1
            metricas['registros_sospechosos'] += 1
            return mapeo[texto]
        return valor

    @staticmethod
    def _sub_imputar_nulos_vitales(df, metricas=None):
        metricas = metricas or defaultdict(int)
        vitales_criticos = ['presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca', 'saturacion_oxigeno', 'glucosa', 'temperatura']
        fallbacks = {
            'presion_sistolica': 120.0,
            'presion_diastolica': 80.0,
            'frecuencia_cardiaca': 80.0,
            'saturacion_oxigeno': 98.0,
            'glucosa': 100.0,
            'temperatura': 36.6,
        }

        df_out = df.copy()
        for col in vitales_criticos:
            if col not in df_out.columns:
                continue
            mask_nulos = df_out[col].isnull()
            nulos = int(mask_nulos.sum())
            if nulos == 0:
                continue
            media = df_out[col].mean()
            valor_imputacion = fallbacks[col] if pd.isna(media) else media
            df_out[col] = df_out[col].fillna(valor_imputacion)
            metricas['registros_con_nulos_imputados'] += nulos
            metricas[f'nulos_imputados_{col}'] += nulos
            metricas['registros_sospechosos'] += nulos
            logger.warning(
                f"🛡️ Fase 1: Se conservaron {nulos} registros con nulos en '{col}' "
                f"y se imputaron con {valor_imputacion:.2f} para revisión."
            )
        return df_out

    @staticmethod
    def _sub_clasificar_rangos(df, metricas=None):
        metricas = metricas or defaultdict(int)
        df_out = df.copy()
        rangos_fisiologicos = {
            'presion_sistolica': (50, 260),
            'presion_diastolica': (30, 160),
            'saturacion_oxigeno': (0, 100),
            'frecuencia_cardiaca': (20, 240),
            'glucosa': (20, 700),
            'temperatura': (30, 43),
        }
        rangos_clinicos_legacy = {
            'presion_sistolica': (40, 300),
            'presion_diastolica': (30, 200),
            'saturacion_oxigeno': (10, 100),
            'frecuencia_cardiaca': (20, 250),
            'glucosa': (20, 600),
            'temperatura': (15, 45),
        }
        umbrales_peligro_clinico = {
            'presion_sistolica': (90, 180),
            'presion_diastolica': (60, 120),
            'saturacion_oxigeno': (85, 100),
            'frecuencia_cardiaca': (40, 130),
            'glucosa': (50, 300),
            'temperatura': (35, 39.5),
        }
        sospecha_mask = pd.Series(False, index=df_out.index)

        for col, (minimo, maximo) in rangos_fisiologicos.items():
            if col not in df_out.columns:
                continue
            mask = df_out[col].notnull() & ((df_out[col] < minimo) | (df_out[col] > maximo))
            cantidad = int(mask.sum())
            if cantidad:
                metricas['registros_fisiologicamente_imposibles'] += cantidad
                metricas[f'fuera_fisiologico_{col}'] += cantidad
                sospecha_mask |= mask
                logger.warning(
                    f"🧪 Fase 1: {cantidad} registros conservados con '{col}' fuera de rango fisiológico "
                    f"({minimo}-{maximo})."
                )

        for col, (minimo, maximo) in rangos_clinicos_legacy.items():
            if col not in df_out.columns:
                continue
            mask = df_out[col].notnull() & ((df_out[col] < minimo) | (df_out[col] > maximo))
            cantidad = int(mask.sum())
            if cantidad:
                metricas['registros_fuera_rango_clinico_conservados'] += cantidad
                metricas[f'fuera_clinico_legacy_{col}'] += cantidad
                logger.warning(
                    f"🩺 Fase 1: {cantidad} registros conservados con '{col}' fuera del rango clínico previo "
                    f"({minimo}-{maximo}); ya no se descartan por este criterio."
                )

        for col, (minimo, maximo) in umbrales_peligro_clinico.items():
            if col not in df_out.columns:
                continue
            mask = df_out[col].notnull() & ((df_out[col] < minimo) | (df_out[col] > maximo))
            cantidad = int(mask.sum())
            if cantidad:
                metricas['registros_clinicamente_peligrosos_posibles'] += cantidad
                metricas[f'peligro_clinico_{col}'] += cantidad
                logger.info(f"🚨 Fase 1: {cantidad} registros con '{col}' en zona clínicamente peligrosa.")

        if 'presion_sistolica' in df_out.columns and 'presion_diastolica' in df_out.columns:
            mask = (
                df_out['presion_sistolica'].notnull() &
                df_out['presion_diastolica'].notnull() &
                (df_out['presion_diastolica'] >= df_out['presion_sistolica'])
            )
            cantidad = int(mask.sum())
            if cantidad:
                metricas['registros_inconsistencia_interna'] += cantidad
                metricas['diastolica_mayor_igual_sistolica'] += cantidad
                sospecha_mask |= mask
                logger.warning(f"🧪 Fase 1: {cantidad} registros conservados con diastólica >= sistólica.")

        metricas['registros_sospechosos'] += int(sospecha_mask.sum())
        return df_out

    @staticmethod
    def _sub_imputar_metabolicos(df, metricas=None):
        metricas = metricas or defaultdict(int)
        df_out = df.copy()
        columnas_a_imputar = ['colesterol', 'peso', 'altura', 'imc', 'edad']

        for col in columnas_a_imputar:
            if col in df_out.columns and df_out[col].isnull().any():
                nulos_antes = int(df_out[col].isnull().sum())
                media = df_out[col].mean()
                if pd.isna(media):
                    media = 0.0 if col != 'edad' else 40
                df_out[col] = df_out[col].fillna(media)
                metricas['registros_con_nulos_imputados'] += nulos_antes
                metricas[f'nulos_imputados_{col}'] += nulos_antes
                metricas['registros_sospechosos'] += nulos_antes
                logger.info(f"🩹 Imputación ML: Nulos en '{col}' reemplazados por la media estadística ({media:.2f}).")
        return df_out

    @staticmethod
    def _sub_calcular_imc_faltante(df, metricas=None):
        metricas = metricas or defaultdict(int)
        df_out = df.copy()
        if 'imc' in df_out.columns:
            mask_imc_inconsistente = df_out['imc'].isnull() | (df_out['imc'] == 0)
            if mask_imc_inconsistente.any() and 'peso' in df_out.columns and 'altura' in df_out.columns:
                df_out.loc[mask_imc_inconsistente, 'imc'] = (
                    df_out.loc[mask_imc_inconsistente, 'peso'] /
                    (df_out.loc[mask_imc_inconsistente, 'altura'] ** 2)
                )
                metricas['imc_recalculados'] += int(mask_imc_inconsistente.sum())
        return df_out

    @staticmethod
    def _registrar_metricas(metricas):
        if not metricas:
            return
        logger.info("📊 Métricas Fase 1 ETL:")
        for clave, valor in sorted(metricas.items()):
            logger.info(f"   {clave}: {valor}")

    @staticmethod
    def _cargar(df):
        try:
            pacientes_a_crear = []
            criticos_detectados = 0

            # 1. Pre-cargar registros existentes usando TODOS los campos clínicos relevantes
            logger.info("🔍 Extrayendo registros de la BD para control estricto de duplicados...")
            claves_existentes = set(
                Paciente.objects.values_list(
                    'nombres', 'apellidos', 'edad', 'sexo', 'peso', 'altura', 'imc',
                    'presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca',
                    'saturacion_oxigeno', 'temperatura', 'glucosa', 'colesterol',
                    'antecedentes_familiares', 'fumador', 'consumo_alcohol',
                    'actividad_fisica', 'diagnostico_preliminar', 'riesgo_enfermedad'
                )
            )

            # Iteración rápida de alta velocidad con itertuples
            for fila in df.itertuples(index=False):
                es_critico = (
                    float(getattr(fila, 'presion_sistolica', 0) or 0) > 180 or
                    float(getattr(fila, 'presion_diastolica', 0) or 0) > 120 or
                    float(getattr(fila, 'saturacion_oxigeno', 0) or 0) < 85 or
                    float(getattr(fila, 'glucosa', 0) or 0) > 300 or
                    float(getattr(fila, 'frecuencia_cardiaca', 0) or 0) > 130 or
                    float(getattr(fila, 'frecuencia_cardiaca', 0) or 0) < 40 or
                    float(getattr(fila, 'temperatura', 0) or 0) > 39.5 or
                    float(getattr(fila, 'temperatura', 0) or 0) < 35
                )
                if es_critico:
                    criticos_detectados += 1

                def safe_bool(val):
                    if isinstance(val, bool): return val
                    return str(val).strip().lower() in ['true', '1', 'yes', 'si']

                datos_clinicos = {
                    'nombres': str(getattr(fila, 'nombres', 'Paciente Anónimo'))[:150],
                    'apellidos': str(getattr(fila, 'apellidos', 'Anonimizado'))[:150],
                    'edad': int(getattr(fila, 'edad', 0)),
                    'sexo': str(getattr(fila, 'sexo', 'M'))[:1],
                    'peso': float(getattr(fila, 'peso', 0) or 0),
                    'altura': float(getattr(fila, 'altura', 0) or 0),
                    'imc': float(getattr(fila, 'imc', 0) or 0),
                    'presion_sistolica': int(getattr(fila, 'presion_sistolica', 0) or 0),
                    'presion_diastolica': int(getattr(fila, 'presion_diastolica', 0) or 0),
                    'frecuencia_cardiaca': int(getattr(fila, 'frecuencia_cardiaca', 0) or 0),
                    'saturacion_oxigeno': float(getattr(fila, 'saturacion_oxigeno', 0) or 0),
                    'temperatura': float(getattr(fila, 'temperatura', 0) or 0),
                    'glucosa': float(getattr(fila, 'glucosa', 0) or 0),
                    'colesterol': float(getattr(fila, 'colesterol', 0) or 0),
                    'antecedentes_familiares': safe_bool(getattr(fila, 'antecedentes_familiares', False)),
                    'fumador': safe_bool(getattr(fila, 'fumador', False)),
                    'consumo_alcohol': safe_bool(getattr(fila, 'consumo_alcohol', False)),
                    'actividad_fisica': str(getattr(fila, 'actividad_fisica', 'Sedentario'))[:50],
                    'diagnostico_preliminar': str(getattr(fila, 'diagnostico_preliminar', 'Sin Diagnóstico'))[:150],
                    'riesgo_enfermedad': str(getattr(fila, 'riesgo_enfermedad', 'Bajo'))[:50],
                    'fecha_consulta': getattr(fila, 'fecha_consulta', None)
                }

                clave = (
                    datos_clinicos['nombres'], datos_clinicos['apellidos'], datos_clinicos['edad'],
                    datos_clinicos['sexo'], datos_clinicos['peso'], datos_clinicos['altura'], datos_clinicos['imc'],
                    datos_clinicos['presion_sistolica'], datos_clinicos['presion_diastolica'], datos_clinicos['frecuencia_cardiaca'],
                    datos_clinicos['saturacion_oxigeno'], datos_clinicos['temperatura'], datos_clinicos['glucosa'], datos_clinicos['colesterol'],
                    datos_clinicos['antecedentes_familiares'], datos_clinicos['fumador'], datos_clinicos['consumo_alcohol'],
                    datos_clinicos['actividad_fisica'], datos_clinicos['diagnostico_preliminar'], datos_clinicos['riesgo_enfermedad']
                )

                if clave not in claves_existentes:
                    # 💡 CREAMOS LA INSTANCIA EN MEMORIA
                    nuevo_paciente = Paciente(**datos_clinicos)
                    
                    # 💡 CALCULAMOS LOS FLAGS EN MEMORIA DIRECTAMENTE ANTES DE GUARDAR
                    # Reemplazamos la lógica de sync_flags() para asignarla aquí sin hacer .save()
                    nuevo_paciente.critico_flag = bool(nuevo_paciente.critico)
                    nuevo_paciente.sospechoso_flag = bool(nuevo_paciente.sospechoso)
                    nuevo_paciente.riesgo_inconsistente_flag = bool(nuevo_paciente.riesgo_inconsistente)
                    nuevo_paciente.nivel_riesgo_calculado_persistido = nuevo_paciente.nivel_riesgo_calculado
                    
                    pacientes_a_crear.append(nuevo_paciente)
                    claves_existentes.add(clave)

            # 3. Guardamos TODO en una sola consulta SQL limpia y masiva
            if pacientes_a_crear:
                Paciente.objects.bulk_create(pacientes_a_crear)
                # 🔥 El bucle lento e iterator() ha sido completamente eliminado.

            logger.info(f"✅ CARGA EXITOSA: {len(pacientes_a_crear)} registros insertados en la BD.")
            logger.info(f"🚨 Alertas críticas detectadas activas: {criticos_detectados}")
            return True
            
        except Exception as e:
            logger.error(f"💥 Fallo crítico en la carga a la BD: {str(e)}", exc_info=True)
            return False