/**
 * dashboard.js — Panel de Control Analítico
 * HealthAnalytics IPS
 *
 * Etapa 1: Renderiza una vista de bienvenida con KPIs de placeholder.
 * Etapa 4 integrará Chart.js y los datos reales del endpoint /api/dashboard/kpis/.
 */

const DashboardModule = (() => {

  function render() {
    const user = window.Auth?.getUser();
    const rol  = user?.rol || 'Usuario';

    return `
    <div class="view-enter">

      <!-- Cabecera de bienvenida -->
      <div class="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h2 class="mb-1" style="font-family:'Manrope',sans-serif;font-weight:800;color:var(--sura-primary-dark)">
            Bienvenido de nuevo
          </h2>
          <p class="mb-0 text-muted" style="font-size:.875rem">
            <i class="bi bi-calendar3 me-1"></i>
            ${new Date().toLocaleDateString('es-CO', { weekday:'long', year:'numeric', month:'long', day:'numeric' })}
          </p>
        </div>
        <span class="risk-badge risk-badge--low">
          <i class="bi bi-shield-check me-1"></i> Sistema operativo
        </span>
      </div>

      <!-- KPI Cards (placeholder) -->
      <div class="row g-3 mb-4">
        ${_kpiCard('Total Pacientes', '—', 'bi-people-fill', 'primary', 'Pendiente conexión API')}
        ${_kpiCard('Pacientes Críticos', '—', 'bi-exclamation-octagon-fill', 'critical', 'Riesgo crítico activo')}
        ${_kpiCard('Hipertensos', '—', 'bi-activity', 'accent', 'Diagnóstico activo')}
        ${_kpiCard('Último ETL', '—', 'bi-arrow-repeat', 'success', 'Procesos completados')}
      </div>

      <!-- Contenido secundario -->
      <div class="row g-3">
        <!-- Gráfica placeholder -->
        <div class="col-lg-8">
          <div class="sura-card h-100">
            <div class="sura-card-header">
              <h3 class="sura-card-title">
                <i class="bi bi-bar-chart-line me-2" style="color:var(--sura-accent)"></i>
                Distribución de Riesgo
              </h3>
              <span class="badge" style="background:var(--sura-bg-neutral);color:var(--sura-text-muted);font-size:.7rem">
                Disponible en Etapa 4
              </span>
            </div>
            <div class="empty-state">
              <i class="bi bi-bar-chart-line empty-state__icon"></i>
              <p class="empty-state__title">Gráficas en desarrollo</p>
              <p class="empty-state__text">
                La integración de Chart.js y los datos analíticos estará disponible en la Etapa 4.
              </p>
            </div>
          </div>
        </div>

        <!-- Actividad reciente placeholder -->
        <div class="col-lg-4">
          <div class="sura-card h-100">
            <div class="sura-card-header">
              <h3 class="sura-card-title">
                <i class="bi bi-clock-history me-2" style="color:var(--sura-accent)"></i>
                Actividad Reciente
              </h3>
            </div>
            <div class="empty-state">
              <i class="bi bi-clock empty-state__icon"></i>
              <p class="empty-state__title">Sin actividad registrada</p>
              <p class="empty-state__text">Los eventos recientes aparecerán aquí.</p>
            </div>
          </div>
        </div>
      </div>

    </div>`;
  }

  function _kpiCard(label, value, icon, variant, sub) {
    return `
    <div class="col-6 col-xl-3">
      <div class="kpi-card">
        <div class="d-flex align-items-start justify-content-between">
          <span class="kpi-card__label">${label}</span>
          <div class="kpi-card__icon kpi-card__icon--${variant}">
            <i class="bi ${icon}"></i>
          </div>
        </div>
        <div class="kpi-card__value">${value}</div>
        <div class="kpi-card__delta kpi-card__delta--flat">
          <i class="bi bi-info-circle"></i> ${sub}
        </div>
      </div>
    </div>`;
  }

  return { render };
})();

window.DashboardModule = DashboardModule;