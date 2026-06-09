# Documentación de Endpoints - HealthAnalytics IPS

> **Nota:** El parámetro `format` del endpoint de exportación se renombró a `export_format` para evitar conflicto con palabras reservadas internas de Django.

---

## Módulo: Autenticación

### `POST /api/auth/login/`
- **Propósito:** Obtener tokens JWT (access + refresh) y usuario autenticado.
- **Roles permitidos:** Público (no requiere auth).
- **Body JSON:**
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```
- **Respuesta 200:**
  ```json
  {
    "refresh": "eyJ...",
    "access": "eyJ...",
    "rol": "Administrador"
  }
  ```

### `POST /api/auth/refresh/`
- **Propósito:** Renovar token de acceso usando el refresh token.
- **Roles permitidos:** Público.
- **Body JSON:**
  ```json
  { "refresh": "eyJ..." }
  ```
- **Respuesta 200:**
  ```json
  { "access": "eyJ..." }
  ```

---

## Módulo: Pacientes

### `GET /api/pacientes/`
- **Propósito:** Obtener listado paginado de pacientes.
- **Roles permitidos:** `Administrador`, `Médico`.
- **Query params opcionales:**
  - `search`: búsqueda por nombre o apellido (case-insensitive).
  - `riesgo`: filtrar por nivel de riesgo (`Bajo`, `Medio`, `Alto`, `Crítico`).
- **Respuesta 200 (JSON paginado):**
  ```json
  {
    "count": 13689,
    "next": "url_siguiente",
    "previous": null,
    "results": [...]
  }
  ```

### `GET /api/pacientes/{id}/`
- **Propósito:** Obtener detalle de un paciente por ID.
- **Roles permitidos:** `Administrador`, `Médico`.

### `POST /api/pacientes/upload/`
- **Propósito:** Cargar archivo CSV/XLSX con datos de pacientes para procesamiento ETL.
- **Roles permitidos:** `Administrador`, `Analista`.
- **Body:** `multipart/form-data` con campo `archivo`.

### `POST /api/etl/run/`
- **Propósito:** Ejecutar el proceso ETL (Extracción, Transformación, Carga).
- **Roles permitidos:** `Administrador`, `Analista`.

### `GET /api/etl/history/`
- **Propósito:** Obtener historial de ejecuciones ETL.
- **Roles permitidos:** `Administrador`, `Analista`.

---

## Módulo: Reportes (Exportación)

### `GET /api/reportes/export/?export_format={formato}`
- **Propósito:** Exportar datos de pacientes en CSV, Excel o PDF con diseño landscape.
- **Roles permitidos:** `Administrador`, `Médico`, `Analista`.
- **Método HTTP:** `GET`
- **Query params obligatorios:**
  - `export_format`: `csv`, `excel` o `pdf`
- **Query params opcionales:**
  - `search`: búsqueda por nombre o apellido.
  - `riesgo`: filtrar por nivel de riesgo.
  - `fecha_desde`: fecha inicial (`YYYY-MM-DD`).
  - `fecha_hasta`: fecha final (`YYYY-MM-DD`).
- **Validación:** `fecha_desde` no puede ser posterior a `fecha_hasta`.
- **Respuesta:**
  - **Content-Type:** según formato:
    - `text/csv` para CSV
    - `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` para Excel
    - `application/pdf` para PDF
  - **Content-Disposition:** `attachment; filename="pacientes.{ext}"`
  - **Cuerpo:** binario del archivo generado.

---

## Módulo: Analytics

### `GET /api/dashboard/kpis/`
- **Propósito:** Obtener KPIs globales y estadísticas descriptivas.
- **Roles permitidos:** `Administrador`, `Médico`, `Analista`.
- **Respuesta 200:**
  ```json
  {
    "estado": "EXITOSO",
    "datos": {
      "kpis_globales": {
        "total_registros": 1801,
        "pacientes_criticos": 329,
        "pacientes_hipertensos": 715,
        ...
      },
      "estadistica_descriptiva": { ... },
      "segmentaciones": { ... }
    }
  }
  ```

---

## Módulo: ML

### `POST /api/ml/prediccion/`
- **Propósito:** Predecir riesgo de enfermedad para nuevos datos clínicos.
- **Roles permitidos:** `Administrador`, `Médico`.
- **Body JSON:**
  ```json
  {
    "edad": 55,
    "presion_sistolica": 120,
    "glucosa": 100,
    ...
  }
  ```
- **Respuesta 200:**
  ```json
  { "estado": "EXITOSO", "riesgo_predicho": "Medio" }
  ```

---

## Mapa de Rutas

| Ruta | Método | Vista | Roles permitidos |
|------|--------|-------|-------------------|
| `/api/auth/login/` | POST | `TokenObtainPairView` | Público |
| `/api/auth/refresh/` | POST | `TokenRefreshView` | Público |
| `/api/pacientes/` | GET | `PacienteListAPIView` | Admin, Médico |
| `/api/pacientes/{id}/` | GET | `PacienteDetailAPIView` | Admin, Médico |
| `/api/pacientes/upload/` | POST | `PacientesUploadView` | Admin, Analista |
| `/api/etl/run/` | POST | `ETLRunView` | Admin, Analista |
| `/api/etl/history/` | GET | `ETLHistoryView` | Admin, Analista |
| `/api/reportes/export/` | GET | `ReportesExportAPIView` | Admin, Médico, Analista |
| `/api/dashboard/kpis/` | GET | `DashboardKPIsAPIView` | Admin, Médico, Analista |
| `/api/ml/prediccion/` | POST | `PrediccionRiesgoAPIView` | Admin, Médico |

---

## Guía de Implementación Frontend

### 1. Almacenamiento del Token
Tras login exitoso, guardar `access` token en `localStorage` o `sessionStorage`:

```javascript
const { access } = await response.json();
localStorage.setItem('access_token', access);
```

### 2. Headers de Autenticación
Incluir en toda petición autenticada:

```javascript
headers: {
  'Authorization': `Bearer ${localStorage.getItem('access_token')}`
}
```

### 3. Exportación de Reportes
**Endpoint:** `GET /api/reportes/export/?export_format={formato}`

```javascript
const exportarPacientes = async (formato, filtros = {}) => {
  const params = new URLSearchParams({ export_format: formato, ...filtros });
  const response = await fetch(`/api/reportes/export/?${params}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    }
  });

  if (!response.ok) throw new Error('Error en exportación');

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `pacientes.${formato === 'excel' ? 'xlsx' : formato}`;
  a.click();
  window.URL.revokeObjectURL(url);
};

// Uso:
exportarPacientes('pdf'); // Abre selector de guardado
exportarPacientes('excel', { riesgo: 'Alto', fecha_desde: '2024-01-01' });
```

### 4. Consideraciones

- **PDF Landscape:** El archivo PDF se genera en orientación horizontal (landscape) con tabla compacta.
- **Streaming:** Para CSV se usa streaming fila por fila (no carga todo en RAM).
- **Filtros aplicables:** `search`, `riesgo`, `fecha_desde`, `fecha_hasta`.
- **Validación:** Si `fecha_desde > fecha_hasta`, el backend retorna `400`.
- **Roles:** Verificar rol del usuario antes de mostrar opciones de exportación en UI.
