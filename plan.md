# Diagnóstico y plan de acción: ocultar métricas ML para usuarios médicos

## Objetivo

Evitar que la sección de “Métricas ML y Modelos” se muestre o cargue para usuarios con rol `Médico`, manteniendo disponible la funcionalidad de predicción ML para ese mismo perfil.

---

## Diagnóstico

### Archivos revisados

- `frontend/index.html`
- `frontend/js/ml.js`
- `frontend/js/app.js`
- `frontend/js/auth.js`

### Comportamiento actual

El módulo ML está definido en `frontend/index.html:233-389` e incluye dos áreas claramente separadas:

1. Tarjeta de métricas y modelos
   - `frontend/index.html:238-263`
   - Botón `#btn-ml-metricas`
   - Contenedor `#ml-modelos-metricas`
   - Endpoint llamado: `/api/ml/metricas/`

2. Formulario y resultado de predicción
   - `frontend/index.html:265-388`
   - Formulario `#form-ml`
   - Botón `#btn-predecir`
   - Endpoint llamado: `/api/ml/prediccion/`

El rol del usuario se guarda en `localStorage` durante el login:

- `frontend/js/auth.js:138-143`

El rol se lee en `window.showApp()`:

- `frontend/js/app.js:43-54`

Actualmente, para usuarios con rol `Médico`, solo se oculta/deshabilita la sección ETL:

- `frontend/js/app.js:49-54`

La sección de métricas ML no tiene ninguna restricción por rol.

### Punto crítico

La función que carga las métricas está en `frontend/js/ml.js:165-196`:

```js
async function fetchMlMetricas() {
  const res = await fetchWithAuth('/api/ml/metricas/', { method: 'GET' });
  ...
}
```

Esto significa que, si el botón `#btn-ml-metricas` queda visible para un médico, el endpoint `/api/ml/metricas/` puede ser solicitado desde el navegador.

---

## Problema detectado

La sección “Métricas ML y Modelos” es visible para todos los usuarios que pueden entrar a la vista ML, incluyendo médicos. Para un usuario con rol `Médico`, esa tarjeta no debe mostrarse ni debe ejecutar la carga de métricas.

---

## Solución recomendada

Aplicar una restricción en frontend con dos niveles:

1. Ocultar la tarjeta completa de métricas cuando el rol sea `Médico`.
2. Bloquear la carga del endpoint `/api/ml/metricas/` si el rol es `Médico`, incluso si el botón existe por alguna razón.

La predicción ML debe seguir disponible para médicos.

---

## Cambios propuestos

### 1. Identificar la tarjeta de métricas

En `frontend/index.html`, agregar un `id` al contenedor de la tarjeta de métricas.

Estado actual aproximado:

```html
<div class="row g-3 mb-4">
```

Cambio recomendado:

```html
<div id="ml-metricas-card" class="row g-3 mb-4">
```

Esto permite ocultar solo la tarjeta de métricas sin afectar el formulario de predicción.

---

### 2. Crear helper de rol médico

En `frontend/js/ml.js`, agregar una función centralizada para validar el rol:

```js
function isUsuarioMedico() {
  return localStorage.getItem('rol') === 'Médico';
}
```

También puede agregarse una función para renderizar el mensaje de restricción:

```js
function renderMlMetricasRestringidas() {
  const container = document.getElementById('ml-modelos-metricas');
  if (!container) return;

  container.innerHTML = `
    <div class="text-center text-muted py-4">
      <i class="bi bi-shield-lock fs-1 d-block mb-2 opacity-25"></i>
      <p class="small mb-0">Las métricas del modelo no están disponibles para tu perfil.</p>
    </div>
  `;
}
```

---

### 3. Ocultar métricas al inicializar ML

En `initMl()` de `frontend/js/ml.js`, antes de conectar eventos del botón de métricas:

```js
const metricasCard = document.getElementById('ml-metricas-card');
const containerMetricas = document.getElementById('ml-modelos-metricas');

if (isUsuarioMedico()) {
  if (metricasCard) metricasCard.classList.add('d-none');
  if (containerMetricas) renderMlMetricasRestringidas();
}
```

Esto evita que el médico vea la tarjeta de métricas.

---

### 4. No registrar el evento de carga para médicos

Dentro de `initMl()`, proteger el listener del botón:

```js
const btnMetricas = document.getElementById('btn-ml-metricas');
if (btnMetricas && !isUsuarioMedico()) {
  btnMetricas.addEventListener('click', (e) => {
    e.preventDefault();
    fetchMlMetricas();
  });
}
```

Así, aunque el botón exista en el DOM, no ejecutará `fetchMlMetricas()` para médicos.

---

### 5. Proteger `fetchMlMetricas()` como defensa adicional

Agregar una validación al inicio de `fetchMlMetricas()`:

```js
async function fetchMlMetricas() {
  if (isUsuarioMedico()) {
    const container = document.getElementById('ml-modelos-metricas');
    if (container) renderMlMetricasRestringidas();
    return;
  }

  const btn = document.getElementById('btn-ml-metricas');
  const container = document.getElementById('ml-modelos-metricas');
  if (!container) return;

  ...
}
```

Este paso evita que cualquier llamada manual o accidental al endpoint se ejecute desde el frontend para un usuario médico.

---

### 6. Mantener predicción ML disponible

No modificar la lógica de:

- `#form-ml`
- `#btn-predecir`
- `/api/ml/prediccion/`

El médico debe poder seguir ejecutando predicciones, pero sin ver ni cargar métricas/modelos.

---

### 7. Validar roles alternativos

Como el backend puede devolver `rol` o `role`, el login actual normaliza así:

```js
localStorage.setItem('rol', data.rol || data.role || 'Médico');
```

El plan usa únicamente `localStorage.getItem('rol')`, por lo que es consistente con el flujo actual.

Si en el futuro se agregan roles como `Administrador`, `Analista`, `Investigador` o `Data Scientist`, la restricción debe aplicarse solo a:

```js
localStorage.getItem('rol') === 'Médico'
```

---

## Tareas de implementación

### Tarea 1: Marcar la tarjeta de métricas

Archivo: `frontend/index.html`

Objetivo:
- Agregar `id="ml-metricas-card"` al contenedor de la tarjeta de métricas.
- No afectar el formulario de predicción.

---

### Tarea 2: Agregar validación por rol en ML

Archivo: `frontend/js/ml.js`

Objetivo:
- Crear `isUsuarioMedico()`.
- Crear `renderMlMetricasRestringidas()`.
- Usar esas funciones para ocultar o bloquear la carga de métricas.

---

### Tarea 3: Proteger inicialización y botón

Archivo: `frontend/js/ml.js`

Objetivo:
- Ocultar `#ml-metricas-card` cuando el rol sea `Médico`.
- Evitar registrar el `click` de `#btn-ml-metricas` para médicos.
- Mantener habilitada la predicción ML.

---

### Tarea 4: Proteger llamada al endpoint

Archivo: `frontend/js/ml.js`

Objetivo:
- Agregar guardia al inicio de `fetchMlMetricas()`.
- Evitar solicitudes a `/api/ml/metricas/` desde frontend cuando el usuario sea médico.

---

### Tarea 5: Validación manual

Archivo: `frontend/js/ml.js` y `frontend/index.html`

Objetivo:
- Iniciar sesión como médico.
- Entrar a la sección ML.
- Confirmar que no se muestra la tarjeta “Métricas ML y Modelos”.
- Confirmar que no se ejecuta la carga del endpoint `/api/ml/metricas/`.
- Confirmar que el formulario de predicción sigue visible y funcional.

---

## Criterios de aceptación

1. Un usuario con rol `Médico` no ve la tarjeta “Métricas ML y Modelos”.
2. Un usuario con rol `Médico` no puede ejecutar `fetchMlMetricas()`.
3. El endpoint `/api/ml/metricas/` no se solicita desde el frontend para médicos.
4. La sección de predicción ML sigue disponible para médicos.
5. Usuarios que no sean médicos siguen viendo y cargando las métricas normalmente.
6. La restricción no depende solo de CSS; también existe una protección en JavaScript.
7. El cambio no afecta el login, logout, dashboard, pacientes, ETL ni reportes.

---

## Nota de seguridad recomendada

La protección frontend evita que la sección se muestre y se cargue desde la interfaz. Si las métricas contienen información sensible del modelo, también conviene validar permisos en backend para `/api/ml/metricas/`, permitiendo solo roles autorizados distintos de `Médico`.
