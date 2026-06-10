/**
 * pacientes.js — Módulo de Pacientes y ETL
 * HealthAnalytics IPS
 *
 * Etapa 1: Placeholder de estructura.
 * Etapa 3 implementará la tabla paginada, filtros y carga CSV.
 */

const PacientesModule = (() => {
  function render() {
    return `
    <div class="view-enter">
      <div class="view-placeholder">
        <i class="bi bi-people view-placeholder__icon"></i>
        <h2 class="view-placeholder__title">Módulo de Pacientes</h2>
        <p class="view-placeholder__desc">
          Tabla paginada con filtros por nombre y nivel de riesgo.<br>
          Disponible en la <strong>Etapa 3</strong>.
        </p>
      </div>
    </div>`;
  }

  return { render };
})();

const EtlModule = (() => {
  function render() {
    return `
    <div class="view-enter">
      <div class="view-placeholder">
        <i class="bi bi-arrow-left-right view-placeholder__icon"></i>
        <h2 class="view-placeholder__title">Panel ETL</h2>
        <p class="view-placeholder__desc">
          Carga de archivos CSV/XLSX y ejecución del proceso ETL.<br>
          Disponible en la <strong>Etapa 3</strong>.
        </p>
      </div>
    </div>`;
  }

  return { render };
})();

window.PacientesModule = PacientesModule;
window.EtlModule = EtlModule;