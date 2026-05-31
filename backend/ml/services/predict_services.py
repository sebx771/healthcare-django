import joblib
import pandas as pd
from pathlib import Path
from django.conf import settings

class PredictService:
    _model = None
    _loaded_model_path = None

    @classmethod
    def _cargar_modelo_dinamico(cls):
        from ..models import MetricasModelos
        
        # 1. Buscar el registro seleccionado como default o el más reciente
        modelo_db = MetricasModelos.objects.filter(default=True).first()
        if not modelo_db:
            modelo_db = MetricasModelos.objects.order_by('-trained_at').first()
            
        if not modelo_db:
            raise FileNotFoundError("No se encontró ningún modelo entrenado.")
        
        # Extraemos el nombre puro del archivo abstrayendo el formato de la ruta
        nombre_archivo = Path(modelo_db.ruta_archivo_joblib).name
        
        # 2. Definición absoluta y limpia de la ruta usando Pathlib para evitar fallos de slashes
        carpeta_modelos = Path(settings.BASE_DIR) / 'ml' / 'saved_models'
        ruta_dinamica = carpeta_modelos / nombre_archivo
        
        # 3. Fallback: Búsqueda manual iterativa en Windows
        if not ruta_dinamica.exists():
            encontrado = False
            if carpeta_modelos.exists():
                for archivo in carpeta_modelos.iterdir():
                    if archivo.name == nombre_archivo:
                        ruta_dinamica = archivo
                        encontrado = True
                        break
            if not encontrado:
                raise FileNotFoundError(f"El archivo binario del modelo no existe en la ruta {carpeta_modelos}.")
        
        # 4. Cargar o reutilizar en memoria
        ruta_absoluta_str = str(ruta_dinamica.resolve())
        if cls._model is None or cls._loaded_model_path != ruta_absoluta_str:
            cls._model = joblib.load(ruta_absoluta_str)
            cls._loaded_model_path = ruta_absoluta_str
            
        return cls._model

    @classmethod
    def predecir_riesgo(cls, datos_paciente: dict) -> str:
        model = cls._cargar_modelo_dinamico()
        
        # 🛠️ CAMBIO: Se añade 'actividad_fisica' a la lista de entrada (16 variables totales)
        features = [
            'edad', 'sexo', 'peso', 'altura', 'imc', 
            'presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca', 
            'glucosa', 'colesterol', 'saturacion_oxigeno', 'temperatura',
            'antecedentes_familiares', 'fumador', 'consumo_alcohol', 'actividad_fisica'
        ]

        df_input = pd.DataFrame([datos_paciente])
        df_input['imc'] = df_input['peso'] / (df_input['altura'] ** 2)

        df_input['sexo'] = df_input['sexo'].map({'M': 1, 'F': 0}).fillna(0).astype(int)
        df_input['antecedentes_familiares'] = df_input['antecedentes_familiares'].astype(int)
        df_input['fumador'] = df_input['fumador'].astype(int)
        df_input['consumo_alcohol'] = df_input['consumo_alcohol'].astype(int)
        
        # 🛠️ CAMBIO: Mapeo idéntico al entrenamiento para procesar el JSON en Postman (Soporta número o texto)
        if isinstance(df_input['actividad_fisica'].iloc[0], str):
            mapeo_actividad = {'Sedentario': 0, 'Moderado': 1, 'Activo': 2}
            df_input['actividad_fisica'] = df_input['actividad_fisica'].map(mapeo_actividad).fillna(0).astype(int)
        else:
            df_input['actividad_fisica'] = df_input['actividad_fisica'].fillna(0).astype(int)

        df_input = df_input[features]
        prediccion_numerica = model.predict(df_input)[0]

        mapeo_inverso = {0: 'Bajo', 1: 'Medio', 2: 'Alto', 3: 'Crítico'}
        return mapeo_inverso.get(prediccion_numerica, 'Desconocido')