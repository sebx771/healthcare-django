# Plan de acción: mejorar falla de credenciales y mantener siempre el login

## Objetivo

Mantener la implementación actual sin migrar a ES Modules.

El único cambio funcional requerido es que el flujo de login sea más seguro:

1. La pantalla de login siempre debe permanecer visible mientras la autenticación falle.
2. Si las credenciales son incorrectas, debe mostrarse `Credenciales inválidas`.
3. Si ocurre cualquier error de red, respuesta inesperada o falta de tokens, el usuario debe quedarse en el login.
4. Nunca se debe llamar a `window.showApp()` en un caso fallido.
5. El dashboard solo debe mostrarse después de una respuesta exitosa y válida del endpoint de login.

---

## Problema actual

Actualmente el login puede fallar o dejar tokens inconsistentes y el flujo puede terminar mostrando la app/dashboard de forma incorrecta.

El comportamiento esperado es:

- Login fallido: quedarse en login.
- Credenciales incorrectas: mostrar `Credenciales inválidas`.
- Error de red: quedarse en login y mostrar mensaje de error.
- Respuesta del servidor sin tokens: quedarse en login.
- Login correcto: guardar tokens y pasar al dashboard.

---

## Alcance

No se migrará a ES Modules.

No se cambiará la arquitectura completa del frontend.

Solo se ajustará la lógica de autenticación en:

- `frontend/js/auth.js`
- `frontend/js/app.js` si actualmente decide entrar automáticamente al dashboard por un token guardado.

---

## Plan propuesto

### 1. Mantener scripts normales

No cambiar los `<script>` de `frontend/index.html` a `type="module"`.

Mantener la carga actual:

```html
<script src="js/app.js"></script>
<script src="js/auth.js"></script>
<script src="js/dashboard.js"></script>
<script src="js/pacientes.js"></script>
<script src="js/ml.js"></script>
<script src="js/reportes.js"></script>
```

---

### 2. Evitar entrada automática al dashboard

`frontend/js/app.js` no debe entrar al dashboard solo porque exista `access_token` en `localStorage`.

El boot inicial debe dejar:

- `#view-login` visible.
- `#view-app` oculto.

La app solo debe mostrarse después de que `frontend/js/auth.js` confirme un login exitoso.

---

### 3. Controlar el submit del formulario de login

En `frontend/js/auth.js`, dentro del evento `submit` de `#form-login`:

1. Limpiar el mensaje de error anterior.
2. Deshabilitar el botón mientras se consulta el backend.
3. Leer usuario y contraseña.
4. Hacer `POST` a:

```txt
/api/auth/login/
```

5. Si la respuesta HTTP no es exitosa:
   - mostrar `Credenciales inválidas`.
   - no llamar a `window.showApp()`.
   - mantener el usuario en login.

6. Si la respuesta HTTP es exitosa pero el JSON no trae tokens:
   - mostrar `Credenciales inválidas` o `Error al iniciar sesión`.
   - no llamar a `window.showApp()`.
   - mantener el usuario en login.

7. Si la respuesta HTTP es exitosa y trae tokens válidos:
   - guardar `access_token`.
   - guardar `refresh_token`.
   - guardar `rol`.
   - guardar `username`.
   - recién ahí llamar a `window.showApp()`.

---

### 4. Manejar cualquier excepción sin salir del login

El bloque del login debe envolver todo en `try/catch`.

Cualquier error debe tratarse como login fallido:

- error de red.
- servidor no disponible.
- JSON inválido.
- respuesta vacía.
- falta de `access_token`.
- falta de `refresh_token`.
- token vacío.
- excepción inesperada.

En todos esos casos:

1. Restaurar el botón de login.
2. Mostrar mensaje de error.
3. Mantener `#view-login` visible.
4. Mantener `#view-app` oculto.
5. No llamar a `window.showApp()`.

---

### 5. Mensajes esperados

Para credenciales incorrectas, el mensaje visible debe ser:

```txt
Credenciales inválidas
```

Para otros errores técnicos, se puede mostrar un mensaje seguro como:

```txt
No se pudo iniciar sesión. Verifique sus credenciales o intente nuevamente.
```

Pero en ningún caso se debe salir del panel de login.

---

### 6. Validar tokens antes de entrar

Antes de llamar a `window.showApp()`, validar que la respuesta tenga:

```txt
access_token
refresh_token
```

Si el backend usa nombres alternativos, aceptar también:

```txt
access
refresh
```

Si falta cualquiera de los dos, tratar como login fallido.

---

### 7. Logout

El logout debe seguir funcionando así:

1. Limpiar:
   - `access_token`
   - `refresh_token`
   - `rol`
   - `username`
2. Llamar a `window.showLogin()`.
3. Mantener el dashboard oculto.

---

### 8. `fetchWithAuth`

`fetchWithAuth` puede seguir en `auth.js`.

Debe mantener este comportamiento:

1. Si recibe `401`, intentar refrescar token.
2. Si el refresh funciona, reintentar la petición.
3. Si el refresh falla:
   - limpiar tokens.
   - llamar a `window.showLogin()`.
   - no permitir continuar en el dashboard.

---

## Validación final

Probar manualmente estos casos:

### Caso 1: carga inicial

Resultado esperado:

- Se muestra el login.
- No se muestra el dashboard.

### Caso 2: credenciales incorrectas

Resultado esperado:

- Se muestra `Credenciales inválidas`.
- El usuario sigue en login.
- No se muestra el dashboard.

### Caso 3: backend no disponible

Resultado esperado:

- Se muestra un mensaje de error.
- El usuario sigue en login.
- No se muestra el dashboard.

### Caso 4: respuesta sin tokens

Resultado esperado:

- Se muestra un mensaje de error.
- El usuario sigue en login.
- No se guarda una sesión inválida.
- No se muestra el dashboard.

### Caso 5: credenciales correctas

Resultado esperado:

- Se guardan los tokens.
- Se guarda usuario y rol.
- Se llama a `window.showApp()`.
- Se muestra el dashboard.

### Caso 6: logout

Resultado esperado:

- Se limpian tokens.
- Se muestra nuevamente el login.
- No se puede acceder al dashboard sin volver a loguearse.

---

## Riesgos a controlar

- No llamar a `window.showApp()` dentro del bloque `catch`.
- No llamar a `window.showApp()` si la respuesta HTTP falla.
- No llamar a `window.showApp()` si falta `access_token`.
- No llamar a `window.showApp()` si falta `refresh_token`.
- No usar `localStorage.getItem('access_token')` en `app.js` para entrar automáticamente al dashboard.
- Restaurar siempre el botón de login en el bloque `finally`.
- Mantener el login visible ante cualquier excepción.
