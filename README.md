# Healthcare Analytics Platform (HealthAnalytics IPS)

Plataforma web para gestionar pacientes y obtener analítica clínica mediante un pipeline ETL (ingesta/transformación/carga) y un modelo de Machine Learning para predicción de riesgo.

El proyecto está compuesto por un **backend Django REST Framework** (APIs con autenticación JWT y endpoints de ETL/ML/Analytics/Reportes) y un **frontend** en JavaScript que consume dichas APIs.

---

## ¿Qué hace el proyecto?

1. **Autenticación**: acceso protegido por JWT con roles (Administrador, Médico, Analista).
2. **ETL de datos**:
   - Carga de datasets (CSV/Excel) de pacientes.
   - Normalización y preparación de datos.
   - Carga de resultados en la base de datos.
   - Historial de ejecuciones.
3. **Pacientes (CRUD/consulta)**: consulta de pacientes ya procesados, con filtros por búsqueda y riesgo.
4. **Analítica / Dashboard**:
   - KPIs globales.
   - Estadística descriptiva y segmentaciones (edad/sexo).
5. **Machine Learning (Inferencia)**:
   - Predicción de nivel de riesgo (`Bajo`, `Medio`, `Alto`, `Crítico`) a partir de variables clínicas.
6. **Reportes**:
   - Exportación de reportes consolidados en **CSV**, **Excel** o **PDF**.

---

## Estructura de carpetas (resumen)

- `backend/`
  - `core/`: configuración de Django (settings, urls, wsgi/asgi).
  - `authentication/`: autenticación y permisos.
  - `pacientes/`: modelos/serializers/vistas/servicios para ingestión ETL y consulta de pacientes.
  - `analytics/`: lógica y endpoints del dashboard.
  - `ml/`: endpoints y servicios para predicción (inferencias) y entrenamiento (si aplica).
  - `reportes/`: generación de reportes y exportación (CSV/Excel/PDF).
- `frontend/`
  - `js/`: consumo de APIs (auth, pacientes, dashboard, ML, reportes).
  - `index.html`: interfaz principal.

---

## Autenticación y seguridad

- Se utiliza **JWT (SimpleJWT)**.
- Endpoints públicos: login y refresh.
- Endpoints protegidos: ETL, pacientes, analytics, ML y reportes según el rol.

---

## Endpoints principales (según la documentación del proyecto)

- `POST /api/auth/login/`
- `POST /api/auth/refresh/`

- `GET /api/dashboard/kpis/`
- `POST /api/ml/prediccion/`

- `POST /api/etl/run/`
- `GET /api/etl/history/`
- `POST /api/pacientes/upload/`

- `GET /api/pacientes/`
- `GET /api/pacientes/<id>/`

- `GET /api/reportes/export/?export_format={csv|excel|pdf}`

> Nota: el parámetro del export usa `export_format`.

---

## Reportes: CSV / Excel / PDF

El módulo `backend/reportes/services.py` genera exportaciones con formato clínico consolidado.

- **CSV**: delimitador `;` y cabeceras en español.
- **Excel**: hoja `Pacientes Clínicos`.
- **PDF**: tabla en orientación *landscape* con estilos compactos.

---

## Requisitos y ejecución

La ejecución exacta puede variar según el entorno, pero normalmente requiere:

- Python + dependencias en `backend/requirements.txt`
- Base de datos configurada vía variables de entorno (`DATABASE_URL`)
- Redis (si el proyecto lo usa para caché)
- Variables de entorno para `SECRET_KEY`, `ORIGIN`, `REDIS_URL`.

---

## Documentación adicional

- `backend/docs/API_ROUTES.md`: documentación detallada de rutas y contratos.
- `REVIEW.md`, `walkhrougth.md`, `plan.md`: contexto del proyecto y cambios realizados.

---

## Estado del proyecto

El proyecto incluye:

- Contratos frontend/backend alineados para ETL, pacientes, dashboard, ML y reportes.
- Pipeline ETL optimizado para reducir cuellos de botella.
- Exportación soportando CSV, Excel y PDF.

---

## Licencia

Pendiente de definir.
