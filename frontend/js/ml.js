/**
 * ml.js — Módulo de Predicción ML
 * HealthAnalytics IPS
 *
 * Etapa 1: Placeholder de estructura.
 * Etapa 5 implementará el formulario clínico completo y la exportación binaria.
 */

const MlModule = (() => {
  function render() {
    return `
    <div class="view-enter">
      <div class="view-placeholder">
        <i class="bi bi-cpu view-placeholder__icon"></i>
        <h2 class="view-placeholder__title">Predicción de Riesgo ML</h2>
        <p class="view-placeholder__desc">
          Formulario clínico para predicción de riesgo de enfermedad
          mediante el modelo de Machine Learning entrenado.<br>
          Disponible en la <strong>Etapa 5</strong>.
        </p>
        <span class="nav-tag mt-2" style="font-size:.75rem;padding:4px 10px">IA — /api/ml/prediccion/</span>
      </div>
    </div>`;
  }

  return { render };
})();

const ReportesModule = (() => {
  function render() {
    return `
    <div class="view-enter">
      <div class="view-placeholder">
        <i class="bi bi-file-earmark-bar-graph view-placeholder__icon"></i>
        <h2 class="view-placeholder__title">Exportación de Reportes</h2>
        <p class="view-placeholder__desc">
          Descarga de datos en CSV, Excel o PDF landscape con filtros avanzados.<br>
          Disponible en la <strong>Etapa 5</strong>.
        </p>
      </div>
    </div>`;
  }

  return { render };
})();

window.MlModule      = MlModule;
window.ReportesModule = ReportesModule;