# Plan: Editar Nivel de Riesgo del Paciente + Indicador de Inconsistencia

## Objetivo

Que médico y admin puedan modificar el campo `riesgo_enfermedad` del paciente, y que al ver la ficha del paciente se muestre claramente cuándo el riesgo asignado difiere del riesgo calculado por el sistema (y cuál es ese valor calculado).

## Cambios

### 1. Panel de información del paciente (read-only)

En `frontend/index.html`, dentro del bloque "Paciente Seleccionado" (col-lg-4), agregar:

- **Riesgo Asignado** — muestra el valor actual de `riesgo_enfermedad`
- **Riesgo Calculado** — muestra `nivel_riesgo_calculado`
- **Badge de inconsistencia** — warning visual cuando `riesgo_inconsistente = true`, indicando qué valor calculó el sistema vs. qué valor tiene asignado

### 2. Formulario de edición (editable)

En `frontend/index.html`, dentro del formulario de campos clínicos (col-lg-8), agregar:

- Select `riesgo_enfermedad` con opciones: `Bajo`, `Medio`, `Alto`, `Crítico`
- Se coloca en la primera fila del grid (antes de Edad) por ser un campo relevante

### 3. Lógica JS

En `frontend/js/pacientes.js`, función `cargarPacienteParaEdicion(pk)`:

- Poblar los nuevos elementos HTML con `p.riesgo_enfermedad` y `p.nivel_riesgo_calculado`
- Si `p.riesgo_inconsistente` es true, mostrar un badge `warning` con tooltip explicativo
- El `riesgo_enfermedad` select del formulario se autocompleta con el valor actual

En `getEdicionPayloadFromForm()`:

- Agregar `riesgo_enfermedad` como string (mismo tratamiento que `sexo`)

### 4. Backend

No requiere cambios. `riesgo_enfermedad` ya es un `CharField` en el modelo, ya está en `Meta.fields` del serializer, y `PacienteRevisarYActualizarView` ya acepta `patch` con cualquier campo. Al guardar, `sync_flags()` recalcula `riesgo_inconsistente_flag` y `nivel_riesgo_calculado_persistido` automáticamente.

## Flujo final

1. Médico abre la ficha de un paciente (click en fila de tabla)
2. Panel muestra: ID, Nombre, Revisado, **Riesgo Asignado**, **Riesgo Calculado**
3. Si el riesgo asignado no coincide con el calculado → badge naranja: *"Riesgo inconsistente: el sistema calculó {nivel} pero el registro tiene {asignado}"*
4. Médico puede cambiar el riesgo mediante el select del formulario
5. Al guardar, el backend persiste el cambio, recalcula flags, invalida cache de analytics
6. La tabla de pacientes y KPIs del dashboard se actualizan al recargar
