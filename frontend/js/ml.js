function getMlRiesgoClass(nivel) {
  const map = { Bajo: 'bajo', Medio: 'medio', Alto: 'alto', Crítico: 'critico' };
  return map[nivel] || 'bajo';
}

function getMlRiesgoIcon(nivel) {
  const map = {
    Bajo:    'bi-check-circle-fill',
    Medio:   'bi-exclamation-circle-fill',
    Alto:    'bi-exclamation-triangle-fill',
    Crítico: 'bi-x-octagon-fill',
  };
  return map[nivel] || 'bi-dash-circle';
}

function getMlRiesgoDesc(nivel) {
  const map = {
    Bajo:    'El paciente presenta un nivel de riesgo bajo. Se recomienda seguimiento rutinario.',
    Medio:   'El paciente presenta un nivel de riesgo moderado. Se sugieren controles periódicos.',
    Alto:    'El paciente presenta un nivel de riesgo alto. Se recomienda atención especializada.',
    Crítico: 'El paciente presenta un nivel de riesgo crítico. Requiere atención médica inmediata.',
  };
  return map[nivel] || 'Resultado no determinado.';
}

function renderMlResultado(data) {
  const nivel = data.riesgo_predicho || data.riesgo || data.nivel || '—';
  const cls   = getMlRiesgoClass(nivel);
  const icon  = getMlRiesgoIcon(nivel);
  const desc  = getMlRiesgoDesc(nivel);
  const confianza = data.confianza !== undefined ? `${(data.confianza * 100).toFixed(1)}%` : null;

  document.getElementById('ml-resultado').innerHTML = `
    <div class="resultado-riesgo resultado-${cls}">
      <i class="bi ${icon} fs-1 mb-2 d-block"></i>
      <div class="text-muted small mb-1 text-uppercase fw-semibold" style="letter-spacing:.07em">Nivel de Riesgo Predicho</div>
      <div class="riesgo-nivel mb-3">${nivel}</div>
      ${confianza ? `<div class="mb-2"><span class="badge bg-secondary">Confianza: ${confianza}</span></div>` : ''}
      <p class="small mb-0 text-muted">${desc}</p>
    </div>
  `;
}

function getFieldValue(name) {
  const el = document.querySelector(`[name="${name}"]`);
  return el ? el.value.trim() : '';
}

function clearValidationErrors(form) {
  form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
}

function setInvalid(input) {
  input.classList.add('is-invalid');
}

function validarFormularioML(form) {
  clearValidationErrors(form);

  const errores = [];

  const fields = [
    { name: 'edad', min: 0, max: 120, step: 1 },
    { name: 'peso', min: 2.0, max: 250.0, step: 0.1 },
    { name: 'altura', min: 50, max: 250, step: 1 },
    { name: 'presion_sistolica', min: 60, max: 240, step: 1 },
    { name: 'presion_diastolica', min: 40, max: 140, step: 1 },
    { name: 'frecuencia_cardiaca', min: 20, max: 250, step: 1 },
    { name: 'glucosa', min: 40.0, max: 500.0, step: 0.1 },
    { name: 'colesterol', min: 80.0, max: 500.0, step: 0.1 },
    { name: 'saturacion_oxigeno', min: 50.0, max: 100.0, step: 0.1 },
    { name: 'temperatura', min: 35.0, max: 43.0, step: 0.1 },
  ];

  fields.forEach(({ name, min, max }) => {
    const raw = getFieldValue(name);
    const num = parseFloat(raw);

    if (raw === '') {
      errores.push(`${name}: Este campo es obligatorio.`);
      return;
    }

    if (Number.isNaN(num) || num < min || num > max) {
      errores.push(`${name}: Debe estar entre ${min} y ${max}.`);
    }
  });

  const sis = parseFloat(getFieldValue('presion_sistolica'));
  const dia = parseFloat(getFieldValue('presion_diastolica'));
  if (!Number.isNaN(sis) && !Number.isNaN(dia) && sis <= dia) {
    errores.push('presion_sistolica: Debe ser mayor que la presión diastólica.');
  }

  ['sexo', 'actividad_fisica'].forEach(name => {
    if (!getFieldValue(name)) {
      errores.push(`${name}: Seleccione una opción válida.`);
    }
  });

  if (errores.length > 0) {
    const primerCampo = errores[0].split(':')[0];
    const input = document.querySelector(`[name="${primerCampo}"]`);
    if (input) setInvalid(input);
  }

  return errores;
}

function initMl() {
  const form      = document.getElementById('form-ml');
  const btnText   = document.getElementById('ml-text');
  const btnSpin   = document.getElementById('ml-spinner');
  const btnSubmit = document.getElementById('btn-predecir');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const errores = validarFormularioML(form);
    if (errores.length) {
      document.getElementById('ml-resultado').innerHTML = `
        <div class="text-danger small mt-2">
          ${errores[0]}
        </div>`;
      return;
    }

    btnText.innerHTML = '<i class="bi bi-cpu me-2"></i>Procesando...';
    btnSpin.classList.remove('d-none');
    btnSubmit.disabled = true;

    const fd = new FormData(form);
    const payload = {};

    for (const [key, value] of fd.entries()) {
      if (['antecedentes_familiares', 'fumador', 'consumo_alcohol'].includes(key)) {
        payload[key] = true;
      } else if (['edad', 'presion_sistolica', 'presion_diastolica',
                  'frecuencia_cardiaca', 'glucosa', 'colesterol'].includes(key)) {
        payload[key] = parseInt(value, 10);
      } else if (key === 'altura') {
        payload[key] = parseFloat(value) / 100;
      } else if (['peso', 'saturacion_oxigeno', 'temperatura'].includes(key)) {
        payload[key] = parseFloat(value);
      } else {
        payload[key] = value;
      }
    }

    ['antecedentes_familiares', 'fumador', 'consumo_alcohol'].forEach(k => {
      if (!(k in payload)) payload[k] = false;
    });

    try {
      const res = await fetchWithAuth('/api/ml/prediccion/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        if (res.status === 400 && typeof err === 'object') {
          const mensajes = Object.entries(err)
            .filter(([k]) => k !== 'non_field_errors')
            .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
            .join('<br>');
          throw new Error(mensajes || err.non_field_errors?.join(', ') || err.detail || err.message || `Error ${res.status}`);
        }
        throw new Error(err.detail || err.message || `Error ${res.status}`);
      }

      const data = await res.json();

      if (data.estado && data.estado !== 'EXITOSO') {
        throw new Error(data.mensaje || data.message || 'La predicción no pudo completarse');
      }

      renderMlResultado(data);
    } catch (err) {
      document.getElementById('ml-resultado').innerHTML = `
        <div class="alert alert-danger">
          <i class="bi bi-exclamation-triangle me-2"></i>${err.message}
        </div>`;
    } finally {
      btnText.innerHTML = '<i class="bi bi-cpu me-2"></i>Ejecutar Predicción';
      btnSpin.classList.add('d-none');
      btnSubmit.disabled = false;
    }
  });
}
