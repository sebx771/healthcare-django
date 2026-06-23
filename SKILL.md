# HealthAnalytics IPS — Patient Flow Architecture

## Data Flow: Backend → Frontend

```
[DB] → Django Model → DRF Serializer → JSON Response → fetchWithAuth() → JS Render
```

### Endpoints

| Method | Endpoint | View | Purpose |
|--------|----------|------|---------|
| GET | `/api/pacientes/` | `PacienteListAPIView` | Paginated list with search/risk/revision filters |
| GET | `/api/pacientes/<pk>/` | `PacienteDetailAPIView` | Single patient detail |
| POST | `/api/pacientes/<pk>/revisar-y-actualizar/` | `PacienteRevisarYActualizarView` | Patch fields + mark revision atomically |

### Frontend Consumption

1. **`app.js:showSection('pacientes')`** — removes `d-none` from `#section-pacientes`, calls `loadPacientes()`
2. **`pacientes.js:loadPacientes`** — fetches `GET /api/pacientes/` with search/risk/pagination params
3. **`pacientes.js:renderTablaPacientes`** — renders rows with `data-pk`, `cursor:pointer`, alert badges/tooltips
4. **Click row** → `initEdicionImposiblesPanel` delegation catches `tr[data-pk]`, calls `seleccionarPacienteParaEdicion(pk)`, removes `d-none` from `#section-pacientes-edicion`, scrolls to panel
5. **`cargarPacienteParaEdicion`** — fetches `GET /api/pacientes/<pk>/`, fills form fields and revision switch
6. **Save** → `guardarEdicionImposibles` → `POST /api/pacientes/<pk>/revisar-y-actualizar/` with `{patch: {...}, marcar_revisado: bool}`

### Serializer Mapping

The `PacienteSerializer` exposes these groups:

| Group | Fields | Source |
|-------|--------|--------|
| Demographic | `nombres`, `apellidos`, `edad`, `sexo` | Model columns |
| Vitals | `peso`, `altura`, `imc`, `presion_sistolica`, `presion_diastolica`, `frecuencia_cardiaca`, `saturacion_oxigeno`, `temperatura` | Model columns |
| Labs | `glucosa`, `colesterol` | Model columns |
| History | `antecedentes_familiares`, `fumador`, `consumo_alcohol`, `actividad_fisica` | Model columns |
| Diagnosis | `diagnostico_preliminar`, `riesgo_enfermedad`, `fecha_consulta` | Model columns |
| Computed flags | `critico`, `sospechoso`, `riesgo_inconsistente`, `nivel_riesgo_calculado` | `@property` on model |
| Persisted flags | `critico_flag`, `sospechoso_flag`, `riesgo_inconsistente_flag`, `nivel_riesgo_calculado_persistido` | Model columns (pre-calculated) |
| Motives | `motivos_critico`, `motivos_sospecha`, `motivos_riesgo_inconsistente` | `@property` on model |
| Revision | `revisado`, `revision_info` | `SerializerMethodField` → cache |

### Changes Applied

#### `backend/pacientes/serializers.py`
- Removed 11 redundant `ReadOnlyField()` declarations. DRF auto-discovers both `@property` and model fields when listed in `Meta.fields`. Only `revisado` and `revision_info` remain explicit (`SerializerMethodField`).

#### `frontend/js/pacientes.js`
- `get_revisado` now accepts `ids_revisados` from serializer context, reducing N `cache.get()` calls to a single set membership check per page.

#### `frontend/index.html`
- Added `id="section-pacientes-edicion"` to the editing card so JS can find it and remove `d-none` / scroll to it on row click.
- Added `d-none` class so the panel starts hidden and only appears when a patient row is clicked.

### N+1 / Performance

- **Revision status**: The list view injects `ids_revisados` into serializer context. `get_revisado` checks `obj.pk in ids` instead of N individual `cache.get()` calls.
- **No DB N+1**: All computed properties are in-memory (model `@property`). Revision data is cache-backed, not DB.
