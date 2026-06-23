
import json
import logging
import pandas as pd
from django.core.cache import cache
from pacientes.models import Paciente
from pacientes.services import RevisionService

logger = logging.getLogger('an_logger')

class AnalyticsService:
    CACHE_KEY = "dashboard_clinical_kpis"
    CACHE_TIMEOUT = 86400
    CACHE_VERSION_KEY = f"{CACHE_KEY}:version"

    @staticmethod
    def _get_cache_version() -> int:
        v = cache.get(AnalyticsService.CACHE_VERSION_KEY)
        if v is None:
            v = 1
            cache.set(AnalyticsService.CACHE_VERSION_KEY, v, 60 * 60 * 24 * 365)
        return int(v)

    @staticmethod
    def _normalizar_bool_series(s: pd.Series) -> pd.Series:
        if s.dtype == bool:
            return s
        return s.apply(lambda x: x is True or str(x).strip().lower() in ['true', '1', 'yes', 'si'])

    @classmethod
    def obtener_kpis_descriptivos(cls, forzar_recarga=False, filtrar_calidad=None, excluir_revisados=False) -> dict:
        filtrar_calidad = filtrar_calidad or []
        calidad = (filtrar_calidad[0] if filtrar_calidad else 'todos')

        # Cache strategy: TTL corto para filtros de calidad; nada especial por revisados (ya se excluye)
        cache_timeout = 3600 if calidad in {'validos', 'criticos', 'sospechosos', 'inconsistentes'} else cls.CACHE_TIMEOUT

        cache_version = cls._get_cache_version()
        cache_key_full = f"{cls.CACHE_KEY}:v{cache_version}:{calidad}:{excluir_revisados}"

        if not forzar_recarga:
            logger.info("Intentando recuperar KPIs clínicos desde el motor de caché (Redis)...")
            datos_cache = cache.get(cache_key_full)
            if datos_cache:
                logger.info("[HIT] KPIs recuperados exitosamente desde Redis.")
                return json.loads(datos_cache)
            logger.warning("[MISS] No se encontraron KPIs en caché. Calculando de forma nativa.")
        else:
            logger.info("Forzando recarga manual de analítica. Ignorando caché.")

        logger.info("Consultando la tabla de Pacientes en la base de datos relacional...")
        queryset = Paciente.objects.all().values(
            'id',
            'edad', 'sexo',
            'presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca',
            'glucosa', 'colesterol', 'saturacion_oxigeno', 'temperatura',
            'peso', 'altura', 'imc',
            'antecedentes_familiares', 'fumador', 'consumo_alcohol',
            'actividad_fisica',
            'riesgo_enfermedad'
        )

        if not queryset.exists():
            logger.error("❌ ERROR ANALÍTICO: La base de datos no contiene pacientes procesados por el ETL.")
            return {"error": "No hay registros clínicos procesados en el sistema."}

        logger.info(f"Dataset cargado en memoria. Procesando estadísticos para {len(queryset)} registros...")
        df = pd.DataFrame(list(queryset))

        # Normalizaciones numéricas
        for col in [
            'edad',
            'presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca',
            'glucosa', 'saturacion_oxigeno', 'temperatura',
            'peso', 'altura', 'imc', 'colesterol'
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Asegurar presencia en caso de migraciones/ETL incompleto
        for col in ['presion_diastolica','frecuencia_cardiaca','peso','altura','imc','temperatura','saturacion_oxigeno','glucosa','presion_sistolica','riesgo_enfermedad','sexo','fumador']:
            if col not in df.columns:
                df[col] = None

        # Normalizar presencia de sexo/edad como strings numéricos/valores para segmentaciones
        if 'sexo' not in df.columns:
            df['sexo'] = ''
        if 'edad' not in df.columns:
            df['edad'] = pd.Series([None] * len(df), index=df.index)

        df['fumador'] = cls._normalizar_bool_series(df['fumador']) if 'fumador' in df.columns else False

        # --- Flags de calidad (replicando Paciente) ---
        es_critico = (
            (df['presion_sistolica'] > 180) |
            (df['presion_diastolica'] > 120) |
            (df['saturacion_oxigeno'] < 85) |
            (df['glucosa'] > 300) |
            (df['frecuencia_cardiaca'] > 130) |
            (df['frecuencia_cardiaca'] < 40) |
            (df['temperatura'] > 39.5) |
            (df['temperatura'] < 35)
        )

        motivos_sospecha = pd.Series(False, index=df.index)

        # Inconsistencia interna
        if 'presion_sistolica' in df.columns and 'presion_diastolica' in df.columns:
            motivos_sospecha |= (df['presion_diastolica'] >= df['presion_sistolica'])

        # Saturación fuera de rango [0,100]
        motivos_sospecha |= (df['saturacion_oxigeno'].notna() & ((df['saturacion_oxigeno'] < 0) | (df['saturacion_oxigeno'] > 100)))

        # Presiones amplios plausibilidad
        motivos_sospecha |= (df['presion_sistolica'].notna() & ((df['presion_sistolica'] <= 0) | (df['presion_sistolica'] > 280)))
        motivos_sospecha |= (df['presion_diastolica'].notna() & ((df['presion_diastolica'] <= 0) | (df['presion_diastolica'] > 200)))

        # FC plausibilidad [20,240]
        motivos_sospecha |= (df['frecuencia_cardiaca'].notna() & ((df['frecuencia_cardiaca'] <= 0) | (df['frecuencia_cardiaca'] < 20) | (df['frecuencia_cardiaca'] > 240)))

        # Glucosa plausibilidad (y >0)
        motivos_sospecha |= (df['glucosa'].notna() & ((df['glucosa'] <= 0) | (df['glucosa'] < 20) | (df['glucosa'] > 1000)))

        # Temperatura plausibilidad [30,43]
        motivos_sospecha |= (df['temperatura'].notna() & ((df['temperatura'] < 25) | (df['temperatura'] > 45)))

        # IMC razonable (para sospecha)
        if 'imc' in df.columns:
            motivos_sospecha |= (df['imc'].notna() & (df['imc'] > 0) & ((df['imc'] < 10) | (df['imc'] > 80)))

        # IMC vs peso/altura inconsistente
        if all(c in df.columns for c in ['imc', 'altura', 'peso']):
            altura_pos = df['altura'].notna() & (df['altura'] > 0)
            peso_pos = df['peso'].notna() & (df['peso'] > 0)
            mask = altura_pos & peso_pos
            imc_calc = df.loc[mask, 'peso'] / (df.loc[mask, 'altura'] ** 2)
            imc_real = df.loc[mask, 'imc']
            tol = (imc_real.abs() / 0.01).where(imc_real.notna(), 0.01)
            rel_diff = (imc_calc - imc_real).abs() / pd.Series(imc_real, index=imc_real.index).abs().clip(lower=0.01)
            motivos_sospecha.loc[mask] |= (rel_diff > 0.15)

        es_sospechoso = motivos_sospecha

        # riesgo_inconsistente: riesgo_asignado vs nivel_riesgo_calculado
        riesgo_asignado = df['riesgo_enfermedad'].astype(str).str.strip().str.capitalize()
        riesgo_asignado = riesgo_asignado.replace('Crítico', 'Alto')

        # nivel_riesgo_calculado (heurística simple según Paciente)
        nivel_riesgo_calculado = pd.Series('Bajo', index=df.index)
        nivel_riesgo_calculado = nivel_riesgo_calculado.mask(es_critico, 'Alto')

        alteracion_moderada = (
            ((df['presion_sistolica'] >= 140) & (df['presion_sistolica'] <= 180)) |
            ((df['presion_diastolica'] >= 90) & (df['presion_diastolica'] <= 120)) |
            ((df['saturacion_oxigeno'] >= 85) & (df['saturacion_oxigeno'] < 95)) |
            ((df['frecuencia_cardiaca'] >= 90) & (df['frecuencia_cardiaca'] <= 130)) |
            ((df['glucosa'] >= 150) & (df['glucosa'] <= 300)) |
            ((df['temperatura'] >= 37.5) & (df['temperatura'] <= 39.5)) |
            (es_sospechoso)
        )
        nivel_riesgo_calculado = nivel_riesgo_calculado.mask(~es_critico & alteracion_moderada, 'Medio')

        riesgo_inconsistente = (riesgo_asignado != nivel_riesgo_calculado)

        df = df.assign(
            es_critico=es_critico,
            es_sospechoso=es_sospechoso,
            riesgo_inconsistente=riesgo_inconsistente,
        )

        # Excluir revisados si corresponde
        if excluir_revisados:
            ids_revisados = set(RevisionService.obtener_ids_revisados() or [])
            if ids_revisados:
                df = df[~df['id'].isin(ids_revisados)].copy()

        # Aplicar filtro de calidad
        if calidad == 'validos':
            df = df[~df['es_sospechoso']].copy()
        elif calidad == 'criticos':
            df = df[df['es_critico']].copy()
        elif calidad == 'sospechosos':
            df = df[df['es_sospechoso']].copy()
        elif calidad == 'inconsistentes':
            df = df[df['riesgo_inconsistente']].copy()

        if df.empty:
            resultado_final = {
                "kpis_globales": {
                    "total_registros": 0,
                    "pacientes_criticos": 0,
                    "pacientes_hipertensos": 0,
                    "pacientes_diabeticos": 0,
                    "pacientes_fumadores": 0,
                    "riesgo_promedio_poblacional": 'Desconocido',
                    "distribucion_riesgo": {},
                    "pacientes_sospechosos": 0,
                    "pacientes_riesgo_inconsistente": 0,
                },
                "estadistica_descriptiva": {},
                "segmentaciones": {"por_sexo": {}, "por_edad": {}}
            }
            return resultado_final

        # Estadísticas descriptivas (misma idea, pero con más columnas si quieres)
        columnas_clave = ['edad', 'presion_sistolica', 'glucosa', 'saturacion_oxigeno']
        estadisticas = {}
        for col in columnas_clave:
            if col in df.columns:
                serie = pd.to_numeric(df[col], errors='coerce').dropna()
                if not serie.empty:
                    estadisticas[col] = {
                        "media": round(float(serie.mean()), 2),
                        "mediana": round(float(serie.median()), 2),
                        "moda": round(float(serie.mode().iloc[0]), 2),
                        "desviacion_estandar": round(float(serie.std()), 2)
                    }

        total_pacientes = len(df)
        conteo_criticos = int(df['es_critico'].sum())

        # Riesgo promedio poblacional
        mapeo_riesgo = {'bajo': 0, 'medio': 1, 'alto': 2, 'critico': 3, 'crítico': 3, 'critico ': 3}
        riesgo_limpio = df['riesgo_enfermedad'].astype(str).str.strip().str.lower().str.replace('ítico', 'itico', regex=False)
        riesgo_numerico = riesgo_limpio.map(mapeo_riesgo).dropna()
        if not riesgo_numerico.empty:
            promedio_num = round(float(riesgo_numerico.mean()))
            mapeo_inverso = {0: 'Bajo', 1: 'Medio', 2: 'Alto', 3: 'Crítico'}
            riesgo_promedio_label = mapeo_inverso.get(promedio_num, 'Medio')
        else:
            riesgo_promedio_label = 'Desconocido'

        pacientes_sospechosos = int(df['es_sospechoso'].sum())
        pacientes_riesgo_inconsistente = int(df['riesgo_inconsistente'].sum())

        kpis = {
            "total_registros": total_pacientes,
            "pacientes_criticos": conteo_criticos,
            "pacientes_sospechosos": pacientes_sospechosos,
            "pacientes_riesgo_inconsistente": pacientes_riesgo_inconsistente,
            "pacientes_hipertensos": int((df['presion_sistolica'] >= 140).sum()),
            "pacientes_diabeticos": int((df['glucosa'] >= 126).sum()),
            "pacientes_fumadores": int((df['fumador'] == True).sum()),
            "riesgo_promedio_poblacional": riesgo_promedio_label,
            "distribucion_riesgo": df['riesgo_enfermedad'].value_counts().to_dict(),
            "calidad_datos": {
                "validos": int((~df['es_sospechoso']).sum()),
                "sospechosos": pacientes_sospechosos,
                "criticos": conteo_criticos,
                "inconsistentes": pacientes_riesgo_inconsistente,
            },
        }

        segmento_sexo = df['sexo'].value_counts().to_dict() if 'sexo' in df.columns else {}
        bins_edad = [0, 18, 35, 50, 65, 120]
        labels_edad = ['0-17', '18-34', '35-49', '50-64', '65+']
        if 'edad' in df.columns:
            df['rango_edad'] = pd.cut(pd.to_numeric(df['edad'], errors='coerce'), bins=bins_edad, labels=labels_edad)
            segmento_edad = df['rango_edad'].value_counts().to_dict()
        else:
            segmento_edad = {}

        resultado_final = {
            "kpis_globales": kpis,
            "estadistica_descriptiva": estadisticas,
            "segmentaciones": {"por_sexo": segmento_sexo, "por_edad": segmento_edad}
        }

        logger.info("💾 Guardando estructura de analítica en Redis.")
        cache.set(cache_key_full, json.dumps(resultado_final), cache_timeout)
        return resultado_final

    @classmethod
    def invalidar_cache_analitica(cls):
        """Invalidación global: incrementa versión para invalidar todas las variantes."""
        logger.warning("🗑️ Solicitud de invalidación de caché recibida. Invalidando analítica (versionado)...")
        v = cls._get_cache_version() + 1
        cache.set(cls.CACHE_VERSION_KEY, v, 60 * 60 * 24 * 365)
