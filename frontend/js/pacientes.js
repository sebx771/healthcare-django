let paginaActual = 1;
let totalPaginas = 1;
let searchTimeout = null;
let filtroActivo = { search: '', riesgo: '' };

function riesgoBadge(riesgo) {
  const map = { Bajo: 'bajo', Medio: 'medio', Alto: 'alto', Crítico: 'critico' };
  const cls = map[riesgo] || 'bajo';
  return `<span class="badge-riesgo badge-${cls}">${riesgo || '—'}</span>`;
}

function renderTooltipMotivos(motivos) {
  if (!Array.isArray(motivos) || motivos.length === 0) return '';
  // Tooltip simple con lista en texto (sin HTML complejo)
  return motivos.map(m => `• ${m}`).join('\n');
}

function renderTablaPacientes(results) {
  const tbody = document.getElementById('tabla-pacientes');
  if (!results || results.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted py-4">No se encontraron pacientes</td></tr>`;
    return;
  }

  tbody.innerHTML = results.map(p => {
    // Flags de negocio calculadas por el backend
    const riesgoInconsistente = !!p.riesgo_inconsistente;
    const critico = !!p.critico;
    const sospechoso = !!p.sospechoso;

   
    // Nota: si tus respuestas no incluyen motivos, igual resaltamos por banderas.
    const motivosSospecha = p.motivos_sospecha || p.motivosSospecha || [];
    const motivosRiesgo = p.motivos_riesgo_inconsistente || p.motivosRiesgoInconsistente || [];

    const tooltipText = [
      riesgoInconsistente && motivosRiesgo?.length ? renderTooltipMotivos(motivosRiesgo) : '',
      (sospechoso || critico) && motivosSospecha?.length ? renderTooltipMotivos(motivosSospecha) : ''
    ].filter(Boolean).join('\n');

    const hasAlert = riesgoInconsistente || sospechoso || critico;
    const rowClass = hasAlert ? 'table-warning-soft' : '';

    // marcamos alertas en celdas relevantes
    const cellAlertClass = hasAlert ? 'alert-cell' : '';
    const tooltipAttrs = hasAlert && tooltipText ? `data-bs-toggle="tooltip" data-bs-placement="top" title="${tooltipText.replace(/"/g,'"')}"` : '';

    return `
      <tr data-pk="${p.id ?? ''}" class="${rowClass}" style="cursor:pointer">
        <td class="fw-semibold ${cellAlertClass}" ${tooltipAttrs}>${p.nombres || '—'}</td>
        <td class="${cellAlertClass}" ${tooltipAttrs}>${p.apellidos || '—'}</td>
        <td class="${cellAlertClass}" ${tooltipAttrs}>${p.edad ?? '—'}</td>
        <td class="${cellAlertClass}" ${tooltipAttrs}>${p.sexo || '—'}</td>
        <td class="${cellAlertClass}" ${tooltipAttrs}>${p.imc !== undefined ? Number(p.imc).toFixed(1) : '—'}</td>
        <td class="${cellAlertClass}" ${tooltipAttrs}>${p.glucosa ?? '—'}</td>
        <td class="${cellAlertClass}" ${tooltipAttrs}>${p.presion_sistolica ?? '—'}</td>
        <td class="${cellAlertClass}" ${tooltipAttrs}>${p.presion_diastolica ?? '—'}</td>
        <td class="${cellAlertClass}" ${tooltipAttrs}>${riesgoBadge(p.riesgo_enfermedad)}</td>
      </tr>
    `;
  }).join('');

  // Inicializa tooltips de Bootstrap luego de render
  if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));
  }
}

function openPacienteModal(pk) {
  // Si no existe el modal en el DOM, delegamos al panel actual.
  const modalEl = document.getElementById('paciente-modal');
  if (!modalEl) {
    seleccionarPacienteParaEdicion(pk);
    const panelSection = document.getElementById('section-pacientes-edicion');
    if (panelSection) {
      panelSection.classList.remove('d-none');
      panelSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    return;
  }
  // En caso de que exista, lo completamos cargando la API.
  seleccionarPacienteParaEdicion(pk);
  // Nota: tu UX actual reutiliza el panel lateral. Aquí puedes migrar a modal real luego.
}


function buildPacientesUrl(overrides = {}) {
  const params = new URLSearchParams();
  const opts = { ...filtroActivo, ...overrides };
  if (opts.search) params.set('search', opts.search);
  if (opts.riesgo) params.set('riesgo', opts.riesgo);
  params.set('page_size', '100');
  params.set('page', opts.page || paginaActual);
  return `/api/pacientes/?${params.toString()}`;
}

async function loadPacientes(forceRefresh = false) {
  const tbody = document.getElementById('tabla-pacientes');
  tbody.innerHTML = `<tr><td colspan="9" class="text-center py-4"><div class="spinner-border spinner-border-sm text-primary"></div></td></tr>`;
  document.getElementById('btn-prev').disabled = true;
  document.getElementById('btn-next').disabled = true;

  const fetchUrl = buildPacientesUrl();

  try {
    const res = await fetchWithAuth(fetchUrl);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const data = await res.json();

    const results = data.results || data;
    const count   = data.count;
    totalPaginas = Math.ceil(count / 100);

    renderTablaPacientes(results);

    const inicio = (paginaActual - 1) * 100 + 1;
    const fin = Math.min(paginaActual * 100, count);
    document.getElementById('paginacion-info').textContent = `Mostrando ${inicio}-${fin} de ${count} pacientes (Bloque ${paginaActual} de ${totalPaginas})`;

    document.getElementById('btn-prev').disabled = paginaActual <= 1;
    document.getElementById('btn-next').disabled = paginaActual >= totalPaginas;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9"><div class="alert alert-danger m-3">${err.message}</div></td></tr>`;
  }
}

let editPacienteId = null;
let editPacienteNombre = '';
let editPacienteRevision = null;

function initEdicionImposiblesPanel() {
  const btnClear = document.getElementById('btn-clear-edit');
  const btnSave = document.getElementById('btn-save-edit');
  const editSwitch = document.getElementById('edit-revisado-switch');
  const editSwitchLabel = document.getElementById('edit-revisado-label');
  const editAlertas = document.getElementById('edit-alertas');

  if (btnClear) {
    btnClear.addEventListener('click', () => {
      editPacienteId = null;
      editAlertas.textContent = 'Selecciona un paciente para ver alertas.';
      ['edit-paciente-id','edit-paciente-nombre','edit-paciente-revisado','edit-riesgo-asignado','edit-riesgo-calculado'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '—';
      });
      const warningRiesgo = document.getElementById('edit-riesgo-inconsistente-warning');
      if (warningRiesgo) warningRiesgo.classList.add('d-none');
      if (editSwitch) {
        editSwitch.checked = false;
        editSwitch.indeterminate = false;
      }
      if (editSwitchLabel) editSwitchLabel.textContent = 'Sin definir';
      const form = document.getElementById('form-edicion-imposibles');
      if (form) form.reset();
      const result = document.getElementById('edit-result');
      if (result) {
        result.classList.add('d-none');
        result.textContent = '';
      }
    });
  }

  if (editSwitch) {
    editSwitch.addEventListener('change', () => {
      if (!editSwitchLabel) return;
      if (editSwitch.checked) editSwitchLabel.textContent = 'Sí';
      else editSwitchLabel.textContent = 'No';
    });
  }

  if (btnSave) {
    btnSave.addEventListener('click', (e) => {
      e.preventDefault();
      if (!editPacienteId) {
        alert('Selecciona un paciente primero');
        return;
      }
      guardarEdicionImposibles();
    });
  }

  const form = document.getElementById('form-edicion-imposibles');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!editPacienteId) {
        alert('Selecciona un paciente primero');
        return;
      }
      guardarEdicionImposibles();
    });
  }

  // Hook: los pacientes se renderizan en tabla, aquí agregamos event delegation.
  const tbody = document.getElementById('tabla-pacientes');
  if (tbody) {
    tbody.addEventListener('click', (ev) => {
      const row = ev.target.closest('tr[data-pk]');
      if (!row) return;
      const pk = row.getAttribute('data-pk');
      if (!pk) return;

      // “Panel emergente” solo cuando se selecciona un paciente:
      // hacemos visible/activa la sección de edición de datos raros.
      const panelSection = document.getElementById('section-pacientes-edicion');
      if (panelSection) {
        panelSection.classList.remove('d-none');
        panelSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }

      seleccionarPacienteParaEdicion(pk);
    });
  }
}

function seleccionarPacienteParaEdicion(pk) {
  editPacienteId = parseInt(pk, 10);
  const result = document.getElementById('edit-result');
  if (result) {
    result.classList.add('d-none');
    result.textContent = '';
  }
  cargarPacienteParaEdicion(editPacienteId);
}

async function cargarPacienteParaEdicion(pk) {
  try {
    const res = await fetchWithAuth(`/api/pacientes/${pk}/`);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const p = await res.json();

    editPacienteNombre = `${p.nombres || ''} ${p.apellidos || ''}`.trim();
    const elId = document.getElementById('edit-paciente-id');
    const elNombre = document.getElementById('edit-paciente-nombre');
    const elRev = document.getElementById('edit-paciente-revisado');
    if (elId) elId.textContent = p.id ?? pk;
    if (elNombre) elNombre.textContent = editPacienteNombre || '—';
    if (elRev) elRev.textContent = p.revisado === true ? 'Sí' : (p.revisado === false ? 'No' : '—');

    // Switch revisado
    const editSwitch = document.getElementById('edit-revisado-switch');
    const editSwitchLabel = document.getElementById('edit-revisado-label');
    const setSwitch = (val) => {
      if (!editSwitch) return;
      if (val === true) {
        editSwitch.checked = true;
        editSwitch.indeterminate = false;
      } else if (val === false) {
        editSwitch.checked = false;
        editSwitch.indeterminate = false;
      } else {
        editSwitch.checked = false;
        editSwitch.indeterminate = true;
      }
      if (editSwitchLabel) editSwitchLabel.textContent = val === true ? 'Sí' : (val === false ? 'No' : 'Sin definir');
    };
    setSwitch(p.revisado);
    editPacienteRevision = p.revisado;

    // Riesgo asignado vs calculado
    const elRiesgoAsignado = document.getElementById('edit-riesgo-asignado');
    const elRiesgoCalculado = document.getElementById('edit-riesgo-calculado');
    const warningRiesgo = document.getElementById('edit-riesgo-inconsistente-warning');
    if (elRiesgoAsignado) elRiesgoAsignado.textContent = p.riesgo_enfermedad || '—';
    if (elRiesgoCalculado) elRiesgoCalculado.textContent = p.nivel_riesgo_calculado || '—';
    if (warningRiesgo) {
      if (p.riesgo_inconsistente) {
        warningRiesgo.classList.remove('d-none');
        const span = warningRiesgo.querySelector('span');
        if (span) span.textContent =
          `El sistema calculó "${p.nivel_riesgo_calculado}" pero el registro tiene "${p.riesgo_enfermedad}"`;
      } else {
        warningRiesgo.classList.add('d-none');
      }
    }

    // Alertas: usar flags read-only
    const alertas = [];
    if (p.critico) alertas.push('Critico detectado');
    if (p.sospechoso) alertas.push('Sospechoso detectado');
    if (p.riesgo_inconsistente) alertas.push('Riesgo inconsistente detectado');

    const editAlertas = document.getElementById('edit-alertas');
    if (editAlertas) editAlertas.textContent = alertas.length ? alertas.join(' • ') : 'No hay alertas de datos raros.';

    // Autocompletar formulario con valores actuales
    const form = document.getElementById('form-edicion-imposibles');
    if (form) {
      form.reset();
      // rellenar solo los campos que existan en p
      const setInput = (name, value) => {
        const input = form.querySelector(`[name="${name}"]`);
        if (!input) return;
        if (value === null || value === undefined) return;
        input.value = (typeof value === 'boolean') ? (value ? 'true' : 'false') : value;
      };

  ['riesgo_enfermedad','edad','sexo','imc','glucosa','colesterol','fumador','presion_sistolica','presion_diastolica','frecuencia_cardiaca','saturacion_oxigeno','temperatura','antecedentes_familiares','consumo_alcohol','peso','altura'].forEach(n => {
        if (n in p) setInput(n, p[n]);
      });
    }
  } catch (err) {
    const editAlertas = document.getElementById('edit-alertas');
    if (editAlertas) editAlertas.textContent = err.message;
  }
}

function getEdicionPayloadFromForm() {
  const form = document.getElementById('form-edicion-imposibles');
  const payload = {};
  if (!form) return payload;

  const fd = new FormData(form);
  for (const [key, value] of fd.entries()) {
    if (value === '') continue;

    if (['fumador','antecedentes_familiares','consumo_alcohol'].includes(key)) {
      payload[key] = (value === 'true');
    } else if (['edad','presion_sistolica','presion_diastolica','frecuencia_cardiaca'].includes(key)) {
      payload[key] = parseInt(value, 10);
    } else if (key === 'sexo' || key === 'riesgo_enfermedad') {
      payload[key] = value;
    } else {
      payload[key] = parseFloat(value);
    }
  }

  // si no se tocaron campos, evitar PATCH vacío
  return payload;
}

async function guardarEdicionImposibles() {
  try {
    const payload = getEdicionPayloadFromForm();
    if (!Object.keys(payload).length) {
      alert('No hay cambios para guardar');
      return;
    }

    const marcar = document.getElementById('edit-revisado-switch')?.indeterminate ? null : (document.getElementById('edit-revisado-switch')?.checked ?? true);

    // Preferimos endpoint compuesto: guarda patch y revisado
    const res = await fetchWithAuth(`/api/pacientes/${editPacienteId}/revisar-y-actualizar/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patch: payload,
        marcar_revisado: marcar === null ? true : !!marcar,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.message || `Error ${res.status}`);
    }

    const data = await res.json();

    const result = document.getElementById('edit-result');
    if (result) {
      result.classList.remove('d-none');
      result.className = 'mt-3 alert alert-success';
      result.innerHTML = `<i class="bi bi-check-circle me-2"></i>Guardado exitosamente`;
    }

    // Recargar UI
    loadPacientes(true);
    if (typeof loadDashboard === 'function') loadDashboard();
    cargarPacienteParaEdicion(editPacienteId);
  } catch (err) {
    const result = document.getElementById('edit-result');
    if (result) {
      result.classList.remove('d-none');
      result.className = 'mt-3 alert alert-danger';
      result.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i>${err.message}`;
    }
  }
}

function initPacientes() {
  // Panel edición de imposibles/datos raros
  initEdicionImposiblesPanel();


  const searchInput = document.getElementById('search-pacientes');

  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      filtroActivo.search = searchInput.value.trim();
      paginaActual = 1;
      loadPacientes();
    }, 400);
  });

  document.querySelectorAll('.btn-filter').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.btn-filter').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      filtroActivo.riesgo = btn.dataset.riesgo;
      paginaActual = 1;
      loadPacientes();
    });
  });

  document.getElementById('btn-recargar-pacientes').addEventListener('click', () => {
    paginaActual = 1;
    loadPacientes(true);
  });

  document.getElementById('btn-prev').addEventListener('click', () => {
    if (paginaActual > 1) {
      paginaActual--;
      loadPacientes();
    }
  });

  document.getElementById('btn-next').addEventListener('click', () => {
    if (paginaActual < totalPaginas) {
      paginaActual++;
      loadPacientes();
    }
  });

  document.querySelector('.btn-filter[data-riesgo=""]').classList.add('active');

  // Botones especiales (si existen)
  // 'riesgo' usa los valores __inconsistentes__ y __imposibles__.

}
