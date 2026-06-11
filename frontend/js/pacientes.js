let paginaActual = 1;
let totalPaginas = 1;
let searchTimeout = null;
let filtroActivo = { search: '', riesgo: '' };

function riesgoBadge(riesgo) {
  const map = { Bajo: 'bajo', Medio: 'medio', Alto: 'alto', Crítico: 'critico' };
  const cls = map[riesgo] || 'bajo';
  return `<span class="badge-riesgo badge-${cls}">${riesgo || '—'}</span>`;
}

function renderTablaPacientes(results) {
  const tbody = document.getElementById('tabla-pacientes');
  if (!results || results.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted py-4">No se encontraron pacientes</td></tr>`;
    return;
  }
  tbody.innerHTML = results.map(p => `
    <tr>
      <td class="fw-semibold">${p.nombres || '—'}</td>
      <td>${p.apellidos || '—'}</td>
      <td>${p.edad ?? '—'}</td>
      <td>${p.sexo || '—'}</td>
      <td>${p.imc !== undefined ? Number(p.imc).toFixed(1) : '—'}</td>
      <td>${p.glucosa ?? '—'}</td>
      <td>${p.presion_sistolica ?? '—'}</td>
      <td>${p.presion_diastolica ?? '—'}</td>
      <td>${riesgoBadge(p.riesgo_enfermedad)}</td>
    </tr>
  `).join('');
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

async function loadPacientes(url = null) {
  const tbody = document.getElementById('tabla-pacientes');
  tbody.innerHTML = `<tr><td colspan="9" class="text-center py-4"><div class="spinner-border spinner-border-sm text-primary"></div></td></tr>`;
  document.getElementById('btn-prev').disabled = true;
  document.getElementById('btn-next').disabled = true;

  const fetchUrl = url || buildPacientesUrl();

  try {
    const res = await fetchWithAuth(url ? url.replace(new RegExp(`^${API_BASE_URL}`), '') : fetchUrl);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const data = await res.json();

    const results = data.results || data;
    const count   = data.count || results.length;
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

function initPacientes() {
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
}
