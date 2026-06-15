# 1. Usar Python 3.12-slim (Altamente compatible con todas las librerías de ML)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 2. Instalar dependencias del sistema necesarias para compilar librerías de datos
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Asegurar que pip, setuptools y wheel estén actualizados
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 4. Copiar e instalar requerimientos
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r /backend/requirements.txt

# 5. Copiar el resto del proyecto
COPY /backend/ /app/

EXPOSE 8000

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
