# Documentación: Módulo ETL

## Descripción General

El módulo ETL (Extract, Transform, Load) extrae datos clínicos desde archivos CSV/Excel, los limpia y valida, y los carga en la base de datos PostgreSQL. Incluye historial de ejecuciones, deduplicación, imputación de valores faltantes y validación de rangos clínicos.

---

## Estructura de Carpetas

```
pacientes/
├── models/
│   ├── __init__.py
│   ├── paciente.py          # Modelo Paciente (datos clínicos)
│   └── archivo.py           # Modelo ArchivoETL (historial de ejecuciones)
├── services/
│   ├── __init__.py          # Exporta ETLService
│   └── etl_services.py      # Lógica principal del pipeline ETL
├── views/
│   ├── __init__.py
│   ├── etl_views.py         # Vistas API (run, upload, history)
│   └── paciente_views.py    # CRUD de pacientes
├── serializers.py           # Serializers para upload y archivos ETL
├── admin.py
├── apps.py
├── tests.py
├── urls.py                  # Rutas del módulo
├── management/
│   └── commands/
│       └── cargar_datos.py  # Comando CLI: python manage.py cargar_datos
└── migrations/
    ├── 0001_initial.py
    ├── 0002_archivoetl.py
    └── 0003_remove_paciente_id_paciente.py
```

---

## Modelos de Datos

### `Paciente` (`pacientes/models/paciente.py`)

Tabla principal que almacena los registros clínicos procesados por el ETL.

#### Campos

**Demografía y antropometría:**
- `nombres`, `apellidos` (str)
- `edad` (int)
- `sexo` (str): `"M"` o `"F"`
- `peso` (float, kg)
- `altura` (float, m)
- `imc` (float)

**Signos vitales:**
- `presion_sistolica` (int, mmHg)
- `presion_diastolica` (int, mmHg)
- `frecuencia_cardiaca` (int, lpm)
- `saturacion_oxigeno` (float, %)
- `temperatura` (float, °C)
- `glucosa` (float, mg/dL)
- `colesterol` (float, mg/dL)

**Hábitos y antecedentes:**
- `antecedentes_familiares` (bool)
- `fumador` (bool)
- `consumo_alcohol` (bool)
- `actividad_fisica` (str)

**Clínico:**
- `diagnostico_preliminar` (str)
- `riesgo_enfermedad` (str): `"Bajo"`, `"Medio"`, `"Alto"`, `"Crítico"`
- `fecha_consulta` (date, nullable)

#### Propiedades

- `critico` (property): Retorna `True` si:
  - `presion_sistolica > 180` **o**
  - `glucosa > 300` **o**
  - `saturacion_oxigeno < 85`

### `ArchivoETL` (`pacientes/models/archivo.py`)

Registra cada ejecución del pipeline como auditoría:

- `nombre` (str): Nombre del archivo procesado
- `loaded_at` (datetime): Fecha/hora de la ejecución
- `registros_procesados` (int): Cantidad de registros insertados
- `tiempo_ejecucion` (float): Duración en segundos
- `estado` (str): `"EXITOSO"` o `"FALLIDO"`
- `usuario` (FK → User): Usuario que ejecutó la operación

---

## Servicios

### `ETLService` (`pacientes/services/etl_services.py`)

Orquesta las tres fases del pipeline.

#### Métodos públicos

- **`ejecutar_pipeline(ruta_archivo: str, usuario)`**
  - Ejecuta el flujo completo: Extracción → Transformación → Carga.
  - Crea un registro `ArchivoETL` con el resultado.
  - Si es exitoso, invalida la caché de analytics en Redis.

#### `_extraer(ruta_archivo)` *[privado]*

Lee archivos CSV o Excel desde `backend/datasets/` usando `pandas`.

#### `_transformar(df)` *[privado]*

Cadena de 6 sub-etapas:

1. **`_sub_normalizar_estructuras`**
   - Convierte headers a `snake_case`.
   - Elimina unidades en los valores (ej: `"120 mmHg"` → `120`).

2. **`_sub_deduplicar`**
   - Elimina duplicados por la clave compuesta: `(nombres, apellidos, edad)`.

3. **`_sub_purgar_nulos_vitales`**
   - Elimina filas que tengan valores nulos en 6 signos vitales críticos.

4. **`_sub_validar_rangos_clinicos`**
   - Aplica reglas de plausibilidad biológica sobre cada campo clínico.
   - Descarta registros fuera de rangos esperados.

5. **`_sub_imputar_metabolicos`**
   - Imputa valores faltantes en: `colesterol`, `peso`, `altura`, `imc`, `edad` usando la media.

6. **`_sub_calcular_imc_faltante`**
   - Recalcula `imc = peso / altura²` cuando esté ausente.

#### `_cargar(df)` *[privado]*

- Bulk-create de objetos `Paciente` en la base de datos.
- Deduplica en memoria usando un set de claves únicas.

---

## Serializers

### `UploadArchivoSerializer`

Valida archivos subidos vía multipart/form-data:
- Acepta `.csv` y `.xlsx`.
- Verifica tamaño máximo.

### `ArchivoETLSerializer`

Serializa el modelo `ArchivoETL` para respuestas de API.

---

## Vistas y Endpoints

### `ETLRunView` (`pacientes/views/etl_views.py`)

| Método | Ruta | Auth | Roles |
|--------|------|------|-------|
| `POST` | `/api/etl/run/` | JWT | Admin, Analista |

Ejecuta el ETL sobre un archivo previamente cargado. Parámetro opcional:
- `archivo`: nombre del archivo dataset (default: `"dataset_clinico_corregido.xlsx"`)

### `PacientesUploadView` (`pacientes/views/etl_views.py`)

| Método | Ruta | Auth | Roles |
|--------|------|------|-------|
| `POST` | `/api/pacientes/upload/` | JWT | Admin, Analista |

Recibe un archivo multipart, lo guarda en `backend/datasets/` con prefijo de timestamp y ejecuta el pipeline ETL sobre él.

### `ETLHistoryView` (`pacientes/views/etl_views.py`)

| Método | Ruta | Auth | Roles |
|--------|------|------|-------|
| `GET` | `/api/etl/history/` | JWT | Admin, Analista |

Lista todos los registros de `ArchivoETL`, ordenados por fecha descendente.

### `PacienteListAPIView` y `PacienteDetailAPIView` (`pacientes/views/paciente_views.py`)

| Método | Ruta | Auth |
|--------|------|------|
| `GET` | `/api/pacientes/` | Público (sin restricción explícita) |
| `GET` | `/api/pacientes/<id>/` | Público |

---

## Comandos de Management

### Cargar datos desde CLI

```bash
python manage.py cargar_datos
```

Equivale a ejecutar `ETLService.ejecutar_pipeline()` desde la terminal.

---

## Flujo de Ejecución

```
Archivo CSV/Excel
      │
      ▼
  _extraer()           ← pandas lee el archivo
      │
      ▼
  _transformar()       ← 6 sub-etapas
      │
      ▼
  _cargar()            ← bulk_create en Paciente
      │
      ▼
  ArchivoETL           ← registro de auditoría
      │
      ▼  (si exitoso)
  AnalyticsService     ← invalidación de caché Redis
```

---

## Dependencias

| Paquete | Uso |
|---|---|
| `pandas` | Lectura de CSV/Excel y manipulación de DataFrames |
| `openpyxl` | Motor de lectura para archivos `.xlsx` |
| `joblib` | (indirecto, usado por ML) |
| `sklearn` | (indirecto, usado por ML) |
| `settings.BASE_DIR` | Ruta base para `backend/datasets/` |
| `logs/etl.log` | Archivo de log del pipeline |
| `REDIS_URL` | Invalidación de caché de analytics |

---

## Notas Técnicas

- El ETL requiere que la base de datos esté migrada (`python manage.py migrate`).
- Los archivos de dataset deben estar en `backend/datasets/` o subidos vía API.
- Tras una ejecución exitosa, se limpia la caché de analytics para reflejar los nuevos datos en el dashboard.
- Si `Paciente` está vacío, el módulo `ml` no podrá entrenar el modelo.
