
import json
import logging
import pandas as pd
from django.core.cache import cache
from pacientes.models import Paciente

logger = logging.getLogger('an_logger')

class AnalyticsService:
    CACHE_KEY = "dashboard_clinical_kpis"
    CACHE_TIMEOUT = 86400

    @classmethod
    def obtener_kpis_descriptivos(cls, forzar_recarga=False) -> dict:
        """
        Retorna la analítica descriptiva y KPIs desde Redis o base de datos.
        """
        if not forzar_recarga:
            logger.info("Intentando recuperar KPIs clínicos desde el motor de caché (Redis)...")
            datos_cache = cache.get(cls.CACHE_KEY)
            if datos_cache:
                logger.info("[HIT] KPIs recuperados exitosamente desde Redis.")
                return json.loads(datos_cache)
            logger.warning("[MISS] No se encontraron KPIs en caché. Calculando de forma nativa.")
        else:
            logger.info("Forzando recarga manual de analítica. Ignorando caché.")

        logger.info("Consultando la tabla de Pacientes en la base de datos relacional...")
        queryset = Paciente.objects.all().values(
            'edad', 'sexo', 'presion_sistolica', 'glucosa', 'saturacion_oxigeno', 'fumador', 'riesgo_enfermedad'
        )

        if not queryset.exists():
            logger.error("❌ ERROR ANALÍTICO: La base de datos no contiene pacientes procesados por el ETL.")
            return {"error": "No hay registros clínicos procesados en el sistema."}

        logger.info(f"Dataset cargado en memoria. Procesando estadísticos para {len(queryset)} registros...")
        df = pd.DataFrame(list(queryset))

        columnas_clave = ['edad', 'presion_sistolica', 'glucosa', 'saturacion_oxigeno']
        for col in columnas_clave:
            if col in df.columns:
                df[col] = df[col].astype(float)

        estadisticas = {}
        for col in columnas_clave:
            serie = df[col].dropna()
            if not serie.empty:
                estadisticas[col] = {
                    "media": round(float(serie.mean()), 2),
                    "mediana": round(float(serie.median()), 2),
                    "moda": round(float(serie.mode()[0]), 2),
                    "desviacion_estandar": round(float(serie.std()), 2)
                }
        logger.info("Bloque de estadística descriptiva calculado.")

        total_pacientes = len(df)
        condicion_critica = (df['presion_sistolica'] > 180) | (df['glucosa'] > 300) | (df['saturacion_oxigeno'] < 85)
        conteo_criticos = int(condicion_critica.sum())
        
        if conteo_criticos > 0:
            logger.warning(f"ALERTA CRÍTICA: Se detectaron {conteo_criticos} pacientes con signos vitales fuera de límites.")

        # Cálculo del Riesgo Promedio Poblacional (Mapeo numérico)
        mapeo_riesgo = {'bajo': 0, 'medio': 1, 'alto': 2, 'critico': 3}
        riesgo_limpio = df['riesgo_enfermedad'].astype(str).str.strip().str.lower().str.replace('ítico', 'itico', regex=False)
        riesgo_numerico = riesgo_limpio.map(mapeo_riesgo).dropna()
        
        if not riesgo_numerico.empty:
            promedio_num = round(riesgo_numerico.mean())
            mapeo_inverso = {0: 'Bajo', 1: 'Medio', 2: 'Alto', 3: 'Crítico'}
            riesgo_promedio_label = mapeo_inverso.get(promedio_num, 'Medio')
        else:
            riesgo_promedio_label = 'Desconocido'

        kpis = {
            "total_registros": total_pacientes,
            "pacientes_criticos": conteo_criticos,
            "pacientes_hipertensos": int((df['presion_sistolica'] >= 140).sum()),
            "pacientes_diabeticos": int((df['glucosa'] >= 126).sum()),
            "pacientes_fumadores": int((df['fumador'] == True).sum()),
            "riesgo_promedio_poblacional": riesgo_promedio_label,
            "distribucion_riesgo": df['riesgo_enfermedad'].value_counts().to_dict()
        }

        segmento_sexo = df['sexo'].value_counts().to_dict()
        
        bins_edad = [0, 18, 35, 50, 65, 120]
        labels_edad = ['0-17', '18-34', '35-49', '50-64', '65+']
        df['rango_edad'] = pd.cut(df['edad'], bins=bins_edad, labels=labels_edad)
        segmento_edad = df['rango_edad'].value_counts().to_dict()

        resultado_final = {
            "kpis_globales": kpis,
            "estadistica_descriptiva": estadisticas,
            "segmentaciones": {
                "por_sexo": segmento_sexo,
                "por_edad": segmento_edad
            }
        }

        logger.info(f"💾 Guardando estructura de analítica en Redis.")
        cache.set(cls.CACHE_KEY, json.dumps(resultado_final), cls.CACHE_TIMEOUT)
        
        return resultado_final

    @classmethod
    def invalidar_cache_analitica(cls):
        """Elimina la clave de Redis al finalizar el ETL."""
        logger.warning("🗑️ Solicitud de invalidación de caché recibida. Limpiando cache...")
        cache.delete(cls.CACHE_KEY)