# Diagnóstico y plan de acción: rectángulo rojo en login

## Objetivo

Eliminar el rectángulo rojo visible durante la validación de credenciales y mantener un mensaje de error limpio, discreto y profesional en el panel de login.

---

## Diagnóstico

### Archivos revisados

- `frontend/js/auth.js`
- `frontend/index.html`
- `frontend/css/style.css`

### Causa principal

El rectángulo rojo aparece porque el contenedor de error del login está definido en `frontend/index.html:37` con clases de Bootstrap:

```html
<div id="login-error" class="alert alert-danger d-none py-2 small"></div>
```

Luego, en `frontend/js/auth.js:67`, la función `showLoginError()` siempre ejecuta:

```js
errorDiv.textContent = message;
errorDiv.classList.remove('d-none');
```

El problema ocurre porque en `frontend/js/auth.js:102` se llama a:

```js
showLoginError('');
```

Antes de validar las credenciales.

Aunque el mensaje está vacío, la función remueve la clase `d-none`, haciendo visible el `div`. Como el `div` conserva `alert alert-danger`, Bootstrap le aplica fondo rojo, borde rojo y relleno, generando el rectángulo rojo aunque no haya texto.

---

## Problemas detectados

1. `showLoginError('')` muestra el contenedor aunque no exista mensaje.
2. El error usa directamente `alert alert-danger`, que es visualmente fuerte para una validación de login.
3. No se oculta el error al iniciar un nuevo intento de login.
4. El contenedor puede quedar visible con texto vacío si se llama con un string vacío.
5. La interfaz pierde limpieza visual durante la validación porque el bloque rojo aparece antes o durante el proceso.

---

## Solución recomendada

### 1. Corregir `showLoginError()`

La función debe ocultar el contenedor cuando el mensaje esté vacío.

Lógica esperada:

```js
function showLoginError(message) {
  const errorDiv = document.getElementById('login-error');
  if (!errorDiv) return;

  if (!message) {
    errorDiv.textContent = '';
    errorDiv.classList.add('d-none');
    return;
  }

  errorDiv.textContent = message;
  errorDiv.classList.remove('d-none');
}
```

---

### 2. Cambiar el contenedor de error en `index.html`

Reemplazar:

```html
<div id="login-error" class="alert alert-danger d-none py-2 small"></div>
```

Por una clase propia del proyecto:

```html
<div id="login-error" class="login-error d-none"></div>
```

Esto evita depender del estilo fuerte de Bootstrap para errores.

---

### 3. Agregar estilo visual más limpio en `style.css`

Agregar un estilo discreto para el error de login:

```css
.login-error {
  border: 1px solid rgba(220, 53, 69, 0.2);
  border-radius: var(--sura-radius);
  background: rgba(220, 53, 69, 0.06);
  color: #842029;
  padding: 0.55rem 0.75rem;
  font-size: 0.875rem;
  line-height: 1.35;
}
```

Este estilo mantiene la intención de alerta, pero reduce el impacto visual.

---

### 4. Ocultar el error al iniciar sesión correctamente

Después de guardar los tokens y antes de llamar a `window.showApp()`, se recomienda limpiar el mensaje:

```js
showLoginError('');
window.showApp();
```

---

## Tareas de implementación

### Tarea 1: Corregir la función `showLoginError()`

Archivo: `frontend/js/auth.js`

Objetivo:
- Evitar que el contenedor se muestre cuando el mensaje está vacío.
- Ocultar el error cuando se reciba un mensaje vacío.

---

### Tarea 2: Cambiar clases de Bootstrap por clase propia

Archivo: `frontend/index.html`

Objetivo:
- Reemplazar `alert alert-danger d-none py-2 small` por `login-error d-none`.
- Mantener el mismo `id="login-error"`.

---

### Tarea 3: Agregar estilo propio para el error de login

Archivo: `frontend/css/style.css`

Objetivo:
- Crear una alerta de login más limpia y menos invasiva.
- Usar variables existentes del proyecto cuando sea posible.

---

### Tarea 4: Limpiar error al iniciar sesión correctamente

Archivo: `frontend/js/auth.js`

Objetivo:
- Llamar `showLoginError('')` antes de `window.showApp()` en el flujo exitoso.
- Garantizar que el mensaje no persista entre sesiones.

---

## Criterios de aceptación

1. Al presionar “Iniciar Sesión”, no debe aparecer ningún rectángulo rojo vacío.
2. Si las credenciales son inválidas, debe mostrarse el mensaje de error de forma discreta.
3. Si hay error de red o falta de tokens, el usuario debe permanecer en login.
4. Si el login es exitoso, el mensaje de error debe desaparecer antes de mostrar la app.
5. El diseño debe verse más limpio y profesional durante la validación.
