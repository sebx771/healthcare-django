let chartRiesgo = null;
let chartEdad = null;

const RIESGO_COLORS = {
  Bajo:    'rgba(25,135,84,0.8)',
  Medio:   'rgba(255,193,7,0.85)',
  Alto:    'rgba(253,126,20,0.85)',
  Crítico: 'rgba(220,53,69,0.85)',
};

const RIESGO_BORDER = {
  Bajo:    '#198754',
  Medio:   '#FFC107',
  Alto:    '#FD7E14',
  Crítico: '#DC3545',
};

function renderKpiCards(data) {
  const container = document.getElementById('kpi-cards');
  const kpis = [
    { label: 'Total Registros',      value: data.total_registros     ?? '—', icon: 'bi-people-fill',        color: '#0033A0' },
    { label: 'Pacientes Críticos',   value: data.pacientes_criticos   ?? '—', icon: 'bi-exclamation-triangle-fill', color: '#DC3545' },
    { label: 'Pacientes Sospechosos', value: data.pacientes_sospechosos ?? '—', icon: 'bi-eye-fill', color: '#FFC107' },
    { label: 'Riesgo Inconsistente', value: data.pacientes_riesgo_inconsistente ?? '—', icon: 'bi-shuffle', color: '#FD7E14' },
    { label: 'Riesgo Promedio',      value: data.riesgo_promedio_poblacional ?? '—', icon: 'bi-activity',           color: '#FD7E14' },
    { label: 'Pacientes Hipertensos', value: data.pacientes_hipertensos ?? '—', icon: 'bi-heart-pulse-fill', color: '#E91E63' },
    { label: 'Pacientes Diabéticos', value: data.pacientes_diabeticos ?? '—', icon: 'bi-droplet-fill', color: '#05C3DE' },
    { label: 'Pacientes Fumadores',  value: data.pacientes_fumadores  ?? '—', icon: 'bi-cup-straw-fill', color: '#6f42c1' },
  ];

  container.innerHTML = kpis.map(k => `
    <div class="col-6 col-md-4 col-xl-2">
      <div class="card kpi-card h-100" style="border-left-color:${k.color}">
        <div class="d-flex align-items-start justify-content-between">
          <div>
            <div class="kpi-label mb-1">${k.label}</div>
            <div class="kpi-value" style="color:${k.color}">${k.value}</div>
          </div>
          <i class="bi ${k.icon} kpi-icon" style="color:${k.color}; opacity:0.18; font-size:2rem;"></i>
        </div>
      </div>
    </div>
  `).join('');
}

function initCharts(datos) {
  destroyCharts();

  const ctxRiesgo     = document.getElementById('chart-riesgo');
  const ctxEdad       = document.getElementById('chart-edad');

  const riesgoData = datos?.kpis_globales?.distribucion_riesgo || {};
  chartRiesgo = new Chart(ctxRiesgo, {
    type: 'doughnut',
    data: {
      labels: Object.keys(riesgoData),
      datasets: [{
        data: Object.values(riesgoData),
        backgroundColor: Object.keys(riesgoData).map(k => RIESGO_COLORS[k] || 'rgba(108,117,125,0.7)'),
        borderColor: Object.keys(riesgoData).map(k => RIESGO_BORDER[k] || '#6c757d'),
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom', labels: { padding: 16, font: { size: 12 } } },
      },
      cutout: '60%',
    },
  });

  const edadData = datos?.segmentaciones?.por_edad || {};
  chartEdad = new Chart(ctxEdad, {
    type: 'bar',
    data: {
      labels: Object.keys(edadData),
      datasets: [{
        label: 'Pacientes',
        data: Object.values(edadData),
        backgroundColor: 'rgba(0,51,160,0.7)',
        borderColor: '#0033A0',
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
        x: { grid: { display: false } },
      },
    },
  });
}

function destroyCharts() {
  if (chartRiesgo)    { chartRiesgo.destroy();    chartRiesgo    = null; }
  if (chartEdad)      { chartEdad.destroy();      chartEdad      = null; }
}

async function loadDashboard() {
  try {
    const res = await fetchWithAuth('/api/dashboard/kpis/');
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const data = await res.json();
    const analytics = data.datos || data;
    renderKpiCards(analytics.kpis_globales || analytics);
    initCharts(analytics);
  } catch (err) {
    document.getElementById('kpi-cards').innerHTML = `
      <div class="col-12">
        <div class="alert alert-danger"><i class="bi bi-exclamation-triangle me-2"></i>${err.message}</div>
      </div>`;
  }
}
