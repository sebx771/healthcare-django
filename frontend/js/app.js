// ── ROUTER / APP CONTROLLER ──────────────────────────────────────────────

const VIEWS = ['dashboard', 'pacientes', 'etl', 'ml', 'reportes'];

const VIEW_TITLES = {
  dashboard: 'Dashboard Analítico',
  pacientes: 'Gestión de Pacientes',
  etl:       'Motor ETL',
  ml:        'Predicción ML',
  reportes:  'Exportación de Reportes',
};

let currentView = null;

function showSection(viewId) {
  VIEWS.forEach(v => {
    const el = document.getElementById(`section-${v}`);
    if (el) el.classList.add('d-none');
  });

  const target = document.getElementById(`section-${viewId}`);
  if (target) target.classList.remove('d-none');

  document.querySelectorAll('.sidebar-link').forEach(link => {
    link.classList.toggle('active', link.dataset.view === viewId);
  });

  document.getElementById('topbar-title').textContent = VIEW_TITLES[viewId] || viewId;
  currentView = viewId;

  switch (viewId) {
    case 'dashboard': loadDashboard(); break;
    case 'pacientes': loadPacientes(); break;
    case 'etl':       loadEtlHistory(); break;
  }
}

window.showApp = function () {
  document.getElementById('view-login').classList.add('d-none');
  const appShell = document.getElementById('view-app');
  appShell.classList.remove('d-none');

  const rol = localStorage.getItem('rol') || 'Médico';
  const username = localStorage.getItem('username') || 'Usuario';

  document.getElementById('sidebar-username').textContent = username;
  document.getElementById('sidebar-role').textContent = rol;

  if (rol === 'Médico') {
    const navEtl = document.getElementById('nav-etl');
    if (navEtl) navEtl.style.display = 'none';
    const btnRunEtl = document.getElementById('btn-run-etl');
    if (btnRunEtl) btnRunEtl.disabled = true;
  }

  showSection('dashboard');
};

window.showLogin = function () {
  document.getElementById('view-app').classList.add('d-none');
  document.getElementById('view-login').classList.remove('d-none');
  document.getElementById('form-login').reset();
};

function isLoggedIn() {
  return !!localStorage.getItem('access_token');
}

// ── SIDEBAR ──────────────────────────────────────────────────────────────

function initSidebar() {
  document.querySelectorAll('.sidebar-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const view = link.dataset.view;
      if (view) showSection(view);
      if (window.innerWidth < 768) {
        document.getElementById('sidebar').classList.remove('mobile-open');
      }
    });
  });

  const toggleBtn = document.getElementById('btn-toggle-sidebar');
  toggleBtn.addEventListener('click', () => {
    const sidebar = document.getElementById('sidebar');
    const main    = document.querySelector('.main-content');
    if (window.innerWidth < 768) {
      sidebar.classList.toggle('mobile-open');
    } else {
      sidebar.classList.toggle('collapsed');
      main.classList.toggle('sidebar-collapsed');
    }
  });
}

// ── ETL ───────────────────────────────────────────────────────────────────

async function loadEtlHistory() {
  const tbody = document.getElementById('tabla-etl-history');
  tbody.innerHTML = `<tr><td colspan="5" class="text-center py-3"><div class="spinner-border spinner-border-sm text-primary"></div></td></tr>`;
  try {
    const res = await fetchWithAuth('/api/etl/history/');
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const data = await res.json();
    const list = data.results || data;
    if (!list.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-3">Sin registros de ejecución</td></tr>`;
      return;
    }
    tbody.innerHTML = list.map(row => {
      const estado = row.estado || '—';
      const badgeCls = estado === 'EXITOSO' ? 'success'
                     : estado === 'FALLIDO' ? 'danger'
                     : 'secondary';
      return `<tr>
        <td>${row.id ?? '—'}</td>
        <td>${row.fecha_formateada || row.loaded_at || '—'}</td>
        <td><span class="badge bg-${badgeCls}">${estado}</span></td>
        <td>${row.registros_procesados ?? '—'}</td>
        <td>${row.tiempo_ejecucion !== undefined ? row.tiempo_ejecucion.toFixed(2) + ' seg' : '—'}</td>
        <td class="text-muted small">${row.usuario?.username || '—'}</td>
      </tr>`;
    }).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="alert alert-danger m-2 py-2 small">${err.message}</div></td></tr>`;
  }
}

function initEtl() {
  const btnUpload = document.getElementById('btn-upload');
  const btnRunEtl = document.getElementById('btn-run-etl');

  btnUpload.addEventListener('click', async () => {
    const fileInput = document.getElementById('etl-file');
    const resultDiv = document.getElementById('upload-result');
    if (!fileInput.files.length) {
      resultDiv.className = 'mt-3 alert alert-warning';
      resultDiv.innerHTML = '<i class="bi bi-exclamation-triangle me-2"></i>Selecciona un archivo primero';
      resultDiv.classList.remove('d-none');
      return;
    }

    const uploadText = document.getElementById('upload-text');
    const uploadSpin = document.getElementById('upload-spinner');
    uploadText.innerHTML = '<i class="bi bi-upload me-2"></i>Subiendo...';
    uploadSpin.classList.remove('d-none');
    btnUpload.disabled = true;
    resultDiv.classList.add('d-none');

    try {
      const fd = new FormData();
      fd.append('file', fileInput.files[0]);

      const token = localStorage.getItem('access_token');
      const res = await fetch(`${API_BASE_URL}/api/pacientes/upload/`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: fd,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.message || `Error ${res.status}`);
      }

      const data = await res.json();
      resultDiv.className = 'mt-3 alert alert-success';
      resultDiv.innerHTML = `<i class="bi bi-check-circle me-2"></i>${data.mensaje || data.message || 'Archivo cargado correctamente'}`;
      resultDiv.classList.remove('d-none');
      fileInput.value = '';
    } catch (err) {
      resultDiv.className = 'mt-3 alert alert-danger';
      resultDiv.innerHTML = `<i class="bi bi-x-circle me-2"></i>${err.message}`;
      resultDiv.classList.remove('d-none');
    } finally {
      uploadText.innerHTML = '<i class="bi bi-upload me-2"></i>Subir Archivo';
      uploadSpin.classList.add('d-none');
      btnUpload.disabled = false;
    }
  });

  btnRunEtl.addEventListener('click', async () => {
    const etlText = document.getElementById('etl-text');
    const etlSpin = document.getElementById('etl-spinner');
    const etlRes  = document.getElementById('etl-result');

    etlText.innerHTML = '<i class="bi bi-lightning-charge me-2"></i>Ejecutando...';
    etlSpin.classList.remove('d-none');
    btnRunEtl.disabled = true;
    etlRes.classList.add('d-none');

    try {
      const res = await fetchWithAuth('/api/etl/run/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ archivo: 'dataset_clinico_corregido.xlsx' })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.message || `Error ${res.status}`);
      }
      const data = await res.json();
      etlRes.className = 'mt-3 alert alert-success';
      etlRes.innerHTML = `<i class="bi bi-check-circle me-2"></i>${data.mensaje || data.message || 'ETL ejecutado correctamente'}`;
      etlRes.classList.remove('d-none');
      setTimeout(() => loadEtlHistory(), 800);
    } catch (err) {
      etlRes.className = 'mt-3 alert alert-danger';
      etlRes.innerHTML = `<i class="bi bi-x-circle me-2"></i>${err.message}`;
      etlRes.classList.remove('d-none');
    } finally {
      etlText.innerHTML = '<i class="bi bi-lightning-charge me-2"></i>Ejecutar Motor ETL';
      etlSpin.classList.add('d-none');
      btnRunEtl.disabled = false;
    }
  });
}

// ── LOGOUT ────────────────────────────────────────────────────────────────

function initLogout() {
  document.getElementById('btn-logout').addEventListener('click', () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('rol');
    localStorage.removeItem('username');
    window.showLogin();
  });
}

// ── BOOT ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initAuth();
  initSidebar();
  initPacientes();
  initMl();
  initReportes();
  initEtl();
  initLogout();

  if (isLoggedIn()) {
    window.showApp();
  } else {
    window.showLogin();
  }
});
