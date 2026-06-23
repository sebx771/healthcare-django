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
            exito = cls._cargar(df_limpio, metricas)
            end = time()
            tiempo_total = end - start

            ArchivoETL.objects.create(
                nombre=os.path.basename(ruta_archivo),
                registros_procesados=registros_conteo,
                tiempo_ejecucion=tiempo_total,
                estado='EXITOSO',
                usuario=usuario
            )
            
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

        # 1. Estandarizar nombres de columnas, limpiar unidades y mapear valores textuales clínicos
        df_limpio = cls._sub_normalizar_estructuras(df, metricas)

        # --- FILTRO OBLIGATORIO DE BORRADO POR NULOS EN IDENTIDAD ---
        # Solo eliminamos si faltan estrictamente nombres o apellidos para poder identificar al paciente
        filas_antes_limpieza = len(df_limpio)
        columnas_identidad = ['nombres', 'apellidos']
        df_limpio = df_limpio.dropna(subset=columnas_identidad).copy()
        
        filas_borradas = filas_antes_limpieza - len(df_limpio)
        if filas_borradas > 0:
            metricas['registros_eliminados_por_falta_de_identidad'] += filas_borradas
            logger.warning(f"🗑️ Se eliminaron {filas_borradas} registros por ausencia de nombres o apellidos obligatorios.")

        # 2. Filtrar duplicados en el mismo dataframe (mismo nombre y apellido en el archivo, dejamos el primero)
        df_limpio = cls._sub_deduplicar(df_limpio, metricas)

        # 3. Imputar signos vitales faltantes
        df_limpio = cls._sub_imputar_nulos_vitales(df_limpio, metricas)

        # 4. Clasificar rangos clínicos y fisiológicos sin descartar registros
        df_limpio = cls._sub_clasificar_rangos(df_limpio, metricas)

        # 5. Imputar variables metabólicas y antropométricas faltantes (Colesterol, Peso, Altura, Edad)
        df_limpio = cls._sub_imputar_metabolicos(df_limpio, metricas)

        # 6. Recalcular IMC en base a datos de peso y altura imputados si viene vacío o en 0
        df_limpio = cls._sub_calcular_imc_faltante(df_limpio, metricas)

        logger.info(f"✨ Transformación completada. Registros listos para procesar: {len(df_limpio)}")
        return df_limpio

    @staticmethod
    def _sub_deduplicar(df, metricas=None):
        metricas = metricas or defaultdict(int)
        filas_inicio = len(df)
        
        # Deduplicamos dentro del mismo archivo basándonos en la clave única solicitada
        df_out = df.drop_duplicates(subset=['nombres', 'apellidos'], keep='first').copy()
        
        duplicados = filas_inicio - len(df_out)
        metricas['registros_duplicados_en_archivo'] += duplicados
        if duplicados > 0:
            logger.warning(f"⚠️ Removidos {duplicados} registros duplicados dentro del mismo dataset (clave: nombres + apellidos).")
        return df_out

    @staticmethod
    def _sub_normalizar_estructuras(df, metricas=None):
        metricas = metricas or defaultdict(int)
        df_out = df.copy()

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

        if 'diagnostico_preliminar' in df_out.columns:
            df_out['diagnostico_preliminar'] = df_out['diagnostico_preliminar'].astype(str).str.strip().str.lower()
            mapeo = {
                'hipertencion': 'Hipertensión', 'hipertensíon': 'Hipertensión', 'hipertension': 'Hipertensión',
                'cardiopatia': 'Cardiopatía', 'cardiopatía': 'Cardiopatía',
                'obesidad': 'Obesidad', 'paciente sano': 'Paciente Sano', 'sano': 'Paciente Sano'
            }
            df_out['diagnostico_preliminar'] = df_out['diagnostico_preliminar'].map(mapeo).fillna(df_out['diagnostico_preliminar'].str.capitalize())

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
            logger.info(
                f"🛡️ Imputación Vitales: Se asignaron {nulos} nulos en '{col}' "
                f"con {valor_imputacion:.2f}."
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
    def _cargar(df, metricas):
        try:
            pacientes_a_crear = []
            pacientes_a_actualizar = []
            criticos_detectados = 0

            logger.info("🔍 Indexando la Base de Datos por clave única (nombres, apellidos) para control de rendimiento...")
            # Extraemos los pacientes actuales mapeando su clave al objeto completo de la base de datos
            pacientes_existentes = {
                (p.nombres, p.apellidos): p 
                for p in Paciente.objects.all()
            }

            def safe_bool(val):
                if isinstance(val, bool): return val
                return str(val).strip().lower() in ['true', '1', 'yes', 'si']

            # Iteración en alta velocidad con itertuples
            for fila in df.itertuples(index=False):
                
                # Formatear datos limpios del archivo
                nom_limpio = str(getattr(fila, 'nombres', '')).strip()[:150]
                ape_limpio = str(getattr(fila, 'apellidos', '')).strip()[:150]
                clave_unica = (nom_limpio, ape_limpio)

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

                campos_actualizados = {
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

                if clave_unica in pacientes_existentes:
                    # 💡 SI EXISTE: Actualizamos los campos en la instancia en memoria
                    paciente_obj = pacientes_existentes[clave_unica]
                    for campo, valor in campos_actualizados.items():
                        setattr(paciente_obj, campo, valor)
                    
                    # Recalcular propiedades calculadas/flags antes de guardar en memoria
                    paciente_obj.critico_flag = bool(paciente_obj.critico)
                    paciente_obj.sospechoso_flag = bool(paciente_obj.sospechoso)
                    paciente_obj.riesgo_inconsistente_flag = bool(paciente_obj.riesgo_inconsistente)
                    paciente_obj.nivel_riesgo_calculado_persistido = paciente_obj.nivel_riesgo_calculado
                    
                    pacientes_a_actualizar.append(paciente_obj)
                else:
                    # 💡 NO EXISTE: Creamos la instancia en memoria
                    nuevo_paciente = Paciente(
                        nombres=nom_limpio,
                        apellidos=ape_limpio,
                        **campos_actualizados
                    )
                    nuevo_paciente.critico_flag = bool(nuevo_paciente.critico)
                    nuevo_paciente.sospechoso_flag = bool(nuevo_paciente.sospechoso)
                    nuevo_paciente.riesgo_inconsistente_flag = bool(nuevo_paciente.riesgo_inconsistente)
                    nuevo_paciente.nivel_riesgo_calculado_persistido = nuevo_paciente.nivel_riesgo_calculado
                    
                    pacientes_a_crear.append(nuevo_paciente)
                    # Lo añadimos temporalmente al dict local para evitar duplicados en el mismo lote
                    pacientes_existentes[clave_unica] = nuevo_paciente

            # 3. Operaciones masivas a la base de datos (Ejecución SQL masiva única)
            if pacientes_a_crear:
                Paciente.objects.bulk_create(pacientes_a_crear)
                logger.info(f"🆕 bulk_create: {len(pacientes_a_crear)} nuevos pacientes insertados.")

            if pacientes_a_actualizar:
                campos_del_update = [
                    'edad', 'sexo', 'peso', 'altura', 'imc', 'presion_sistolica', 
                    'presion_diastolica', 'frecuencia_cardiaca', 'saturacion_oxigeno', 
                    'temperatura', 'glucosa', 'colesterol', 'antecedentes_familiares', 
                    'fumador', 'consumo_alcohol', 'actividad_fisica', 'diagnostico_preliminar', 
                    'riesgo_enfermedad', 'fecha_consulta', 'critico_flag', 'sospechoso_flag', 
                    'riesgo_inconsistente_flag', 'nivel_riesgo_calculado_persistido'
                ]
                # Actualización masiva de rendimiento con Django bulk_update
                Paciente.objects.bulk_update(pacientes_a_actualizar, campos_del_update)
                logger.info(f"🔄 bulk_update: {len(pacientes_a_actualizar)} registros de pacientes actualizados.")

            metricas['registros_insertados'] = len(pacientes_a_crear)
            metricas['registros_actualizados'] = len(pacientes_a_actualizar)
            logger.info(f"✅ CARGA FINALIZADA CON ÉXITO.")
            logger.info(f"🚨 Alertas críticas activas en este lote: {criticos_detectados}")
            return True
            
        except Exception as e:
            logger.error(f"💥 Fallo crítico en la carga a la BD: {str(e)}", exc_info=True)
            return False