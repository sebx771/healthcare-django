# 📋 TODO: Roadmap de Endpoints - Proyecto Healthcare-Django

## 🔐 1. Módulo de Autenticación y Seguridad
Este módulo se encarga de la gestión de accesos, emisión de tokens y control de permisos basados en tres roles: **Administrador**, **Médico** y **Analista**.

- [x] `POST /api/auth/login/`
  - **Descripción:** Autenticación de usuarios mediante credenciales.
  - **Retorno:** Token de acceso JWT (Access & Refresh Token) y el rol del usuario asignado.
  - **Permisos:** Público.
- [x] `POST /api/auth/refresh/`
  - **Descripción:** Refrescar el token de acceso expirado utilizando el Refresh Token.
  - **Permisos:** Público.

---

## 📊 2. Módulo de Dashboard y Analítica
- [x] `GET /api/dashboard/kpis/`
  - **Descripción:** Ya implementado. Retorna los KPIs globales, estadística descriptiva (media, mediana, moda, desviación estándar) de variables clave y segmentación demográfica (edad/sexo).
  - **Permisos:** Administrador, Médico, Analista.

---

## 🧠 3. Módulo de Machine Learning (Inferencia)
- [x] `POST /api/predicciones/`
  - **Descripción:** Ya implementado. Recibe el JSON con las variables clínicas de un paciente, calcula el IMC dinámicamente y ejecuta el modelo para predecir el nivel de riesgo (`Bajo`, `Medio`, `Alto`, `Crítico`).
  - **Permisos:** Administrador, Médico.

---

## ⚙️ 4. Módulo ETL e Ingesta de Datos
- [x] `POST /api/etl/run/`
  - **Descripción:** Dispara manualmente el pipeline de Pandas para procesar el dataset base (1800 registros) o externos, aplicando las reglas de normalización y tratamiento de nulos.
  - **Permisos:** Administrador, Analista.
- [x] `POST /api/pacientes/upload/`
  - **Descripción:** Permite la subida manual de nuevos archivos de datos (CSV/Excel) desde el frontend administrativo y valida su formato antes de procesarlos.
  - **Permisos:** Administrador, Analista.
- [x] `GET /api/etl/history/`
  - **Descripción:** Retorna el historial de ejecuciones del proceso ETL (Fecha, usuario ejecutor, registros procesados, tiempo de ejecución y estado exitoso/fallido).
  - **Permisos:** Administrador, Analista.

---

## 👥 5. Módulo CRUD de Pacientes
- [x] `GET /api/pacientes/`
  - **Descripción:** Lista los registros de pacientes limpios en el sistema. Debe soportar filtros por término de búsqueda o categorías de riesgo.
  - **Permisos:** Administrador, Médico.
- [x] `GET /api/pacientes/<int:id>/`
  - **Descripción:** Obtiene el detalle completo del perfil clínico de un paciente específico utilizando su identificador.
  - **Permisos:** Administrador, Médico.

---

## 🖨️ 6. Módulo de Reportes y Exportación
- [x] `GET /api/reportes/export/`
  - **Descripción:** Endpoint para generar y descargar reportes clínicos consolidados filtrados.
  - **Parámetros query aceptados:** `?format=pdf`, `?format=excel`, `?format=csv`.
  - **Permisos:** Administrador, Médico, Analista.

---

## 👥 Matriz de Permisos por Rol (Obligatoria)

| Endpoint | Administrador | Médico | Analista |
| :--- | :---: | :---: | :---: |
| `/api/auth/login/` | ✅ | ✅ | ✅ |
| `/api/dashboard/kpis/` | ✅ | ✅ | ✅ |
| `/api/predicciones/` | ✅ | ✅ | ❌ |
| `/api/etl/run/` | ✅ | ❌ | ✅ |
| `/api/pacientes/upload/` | ✅ | ❌ | ✅ |
| `/api/etl/history/` | ✅ | ❌ | ✅ |
| `/api/pacientes/` (Ver/Detalle) | ✅ | ✅ | ❌ |
| `/api/reportes/export/` | ✅ | ✅ | ✅ |

---

### Instrucciones para el inicio del desarrollo:

1. Utilizaremos `djangorestframework-simplejwt` para manejar la autenticación basada en JWT de forma limpia y estándar.
2. Debemos extender o mapear los usuarios de Django (o sus perfiles/grupos) para soportar de manera estricta los tres roles requeridos: `Administrador`, `Médico`, e `Analista`.
3. Es mandatorio crear clases de permisos personalizadas (`BasePermission` de DRF) para validar las restricciones especificadas en la matriz de permisos.
4. Por flexibilidad del proyecto, no es obligatorio cumplir con una jerarquía estricta de carpetas tipo mono-app, pero el código debe ser modular, limpio y respetar los principios SOLID.

