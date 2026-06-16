# Documentación: Módulo ML (Machine Learning)

## Descripción General

El módulo `ml/` implementa el servicio de predicción de riesgo clínico. Consume datos ya procesados por el ETL, entrena un modelo de clasificación supervisada y expone un endpoint de inferencia en tiempo real.

---

## Estructura de Carpetas

```
ml/
├── __init__.py
├── admin.py                  # Registro de MetricasModelos en Django Admin
├── apps.py                   # Configuración de la app
├── models.py                 # MetricasModelos (metadatos de modelos entrenados)
├── serializers.py            # PredictSerializer (validación de entrada)
├── tests.py                  # Placeholder
├── urls.py                   # Rutas del módulo
├── views.py                  # PrediccionRiesgoAPIView
├── saved_models/             # Archivos .joblib serializados
├── services/
│   ├── __init__.py
│   ├── predict_services.py   # PredictService (inferencia)
│   └── train_services.py     # MLTrainerService (entrenamiento)
├── management/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       └── train_models.py   # Comando: python manage.py train_models
├── migrations/
│   ├── 0001_initial.py
│   └── 0002_metricasmodelos_default.py
└── test_scripts/
    └── test_modelo.py
```

---

## Modelo de Datos

### `MetricasModelos` (`ml/models.py`)

Registra cada versión del modelo entrenado:

- `nombre_modelo`: Nombre del modelo (default: `"RandomForestClassifier"`)
- `trained_at`: Fecha/hora de entrenamiento (auto)
- `accuracy`, `precision`, `recall`, `f1_score`: Métricas de desempeño
- `default`: Booleano. Solo un registro puede ser `True` a la vez
- `matriz_confusion`: Matriz serializada como texto
- `ruta_archivo_joblib`: Ruta al archivo `.joblib` en disco

> Restricción: el método `save()` garantiza que solo un registro esté marcado como default.

---

## Servicios

### `PredictService` (`ml/services/predict_services.py`)

Responsable de la inferencia.

#### Métodos

- **`_cargar_modelo_dinamico()`** *(classmethod)*
  - Busca el modelo marcado como `default=True`. Si no existe, usa el más reciente.
  - Carga el `.joblib` desde `ml/saved_models/` usando `joblib.load()`.
  - Cachea el modelo en memoria (`cls._model`) para evitar recargas repetidas.

- **`predecir_riesgo(datos_paciente: dict) -> str`** *(classmethod)*
  - Recibe un diccionario con 16 variables clínicas.
  - Calcula `imc` automáticamente: `peso / altura²`.
  - Codifica variables categóricas/booleanas a enteros:
    - `sexo`: `M` → 1, `F` → 0
    - Booleanos: `True` → 1, `False` → 0
    - `actividad_fisica`: `Sedentario` → 0, `Moderado` → 1, `Activo` → 2
  - Ejecuta `model.predict()` y mapea el resultado numérico a string:
    - `0 → "Bajo"`, `1 → "Medio"`, `2 → "Alto"`, `3 → "Crítico"`

### `MLTrainerService` (`ml/services/train_services.py`)

Responsable del entrenamiento del modelo.

#### Métodos

- **`extraer_datos_orm()`** *(classmethod)*
  - Extrae todos los registros de `Paciente` desde la base de datos.
  - Aplica el mismo preprocesamiento que la inferencia (mapeos idénticos).
  - Mapea `riesgo_enfermedad` a valores numéricos: `Bajo→0, Medio→1, Alto→2, Crítico→3`.
  - Retorna `(X, y)` listos para entrenar.

- **`ejecutar_kfold_y_entrenar()`** *(classmethod)*
  - Ejecuta validación cruzada K-Fold con `K=5`.
  - Modelo: `RandomForestClassifier(n_estimators=100, random_state=42)`.
  - Calcula métricas promedio: accuracy, precision, recall, f1-score.
  - Entrena modelo final con el 100% de los datos.
  - Serializa con `joblib.dump()` en `ml/saved_models/modelo_riesgo_rf_<timestamp>.joblib`.
  - Crea un registro en `MetricasModelos` con todas las métricas.

---

## Serializers

### `PredictSerializer` (`ml/serializers.py`)

Valida los 16 campos de entrada para inferencia:

| Campo | Tipo | Ejemplo |
|---|---|---|
| `edad` | int | 45 |
| `sexo` | str | `"M"` o `"F"` |
| `peso` | float | 70.5 |
| `altura` | float | 1.75 |
| `imc` | float | 23.4 |
| `presion_sistolica` | int | 120 |
| `presion_diastolica` | int | 80 |
| `frecuencia_cardiaca` | int | 72 |
| `glucosa` | float | 90.0 |
| `colesterol` | float | 180.0 |
| `saturacion_oxigeno` | float | 96.0 |
| `temperatura` | float | 36.5 |
| `antecedentes_familiares` | bool | `True` / `False` |
| `fumador` | bool | `True` / `False` |
| `consumo_alcohol` | bool | `True` / `False` |
| `actividad_fisica` | str | `"Sedentario"`, `"Moderado"`, `"Activo"` |

---

## Vistas y Endpoints

### `PrediccionRiesgoAPIView` (`ml/views.py`)

| Método | Ruta | Auth | Roles |
|--------|------|------|-------|
| `POST` | `/api/ml/prediccion/` | `IsAuthenticated` | Administrador, Médico |

**Request Body:**
```json
{
  "edad": 45,
  "sexo": "M",
  "peso": 80.0,
  "altura": 1.75,
  "imc": 26.1,
  "presion_sistolica": 140,
  "presion_diastolica": 90,
  "frecuencia_cardiaca": 88,
  "glucosa": 110.0,
  "colesterol": 200.0,
  "saturacion_oxigeno": 92.0,
  "temperatura": 37.0,
  "antecedentes_familiares": true,
  "fumador": false,
  "consumo_alcohol": true,
  "actividad_fisica": "Moderado"
}
```

**Response (éxito):**
```json
{
  "estado": "EXITOSO",
  "riesgo_predicho": "Alto"
}
```

**Response (error):**
```json
{
  "error": "No se encontró ningún modelo entrenado."
}
```

---

## Comandos de Management

### Entrenar modelo

```bash
python manage.py train_models
```

Ejecuta `MLTrainerService.ejecutar_kfold_y_entrenar()`. Requiere que el ETL ya haya poblado la tabla `Paciente`.

---

## Dependencias e Integración

| Dependencia | Uso |
|---|---|
| `pacientes.models.Paciente` | Fuente de datos de entrenamiento |
| `pandas` | Preprocesamiento y features |
| `joblib` | Serialización/deserialización del modelo |
| `sklearn` (`RandomForestClassifier`, `KFold`, métricas) | Motor de ML |
| `numpy` | Cálculos matriciales |
| `settings.BASE_DIR` | Ruta base para `ml/saved_models/` |
| `logs/ml.log` | Trazas de entrenamiento e inferencia |

---

## Notas Técnicas

- El modelo se cachea en memoria tras la primera carga. Para usar un modelo nuevo (post-entrenamiento), es necesario reiniciar el servidor.
- El mapeo de `actividad_fisica` debe ser idéntico entre entrenamiento e inferencia.
- El mapeo de riesgos normaliza la ípsilon: `'ítico' → 'itico'` para evitar problemas de encoding.
