const EXTENSION_MAP = { pdf: '.pdf', excel: '.xlsx', csv: '.csv' };
const MIME_MAP = {
  pdf:  'application/pdf',
  excel: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  csv:  'text/csv',
};

function getSelectedFormat() {
  const checked = document.querySelector('input[name="export_format"]:checked');
  return checked ? checked.value : 'pdf';
}

async function exportarReporte() {
  const btnText = document.getElementById('export-text');
  const btnSpin = document.getElementById('export-spinner');
  const btnExp  = document.getElementById('btn-exportar');
  const result  = document.getElementById('export-result');

  const format = getSelectedFormat();
  result.classList.add('d-none');

  btnText.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Generando...';
  btnSpin.classList.remove('d-none');
  btnExp.disabled = true;

  const params = new URLSearchParams({ export_format: format });

  const riesgo = document.getElementById('reporte-riesgo').value;
  const search = document.getElementById('reporte-search').value.trim();
  if (riesgo) params.set('riesgo', riesgo);
  if (search) params.set('search', search);

  try {
    const res = await fetchWithAuth(`/api/reportes/export/?${params.toString()}`, {
      headers: {},
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.message || `Error ${res.status}`);
    }

    const blob = await res.blob();
    const mimeBlob = new Blob([blob], { type: MIME_MAP[format] || blob.type });
    const objectUrl = window.URL.createObjectURL(mimeBlob);

    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = objectUrl;
    a.download = `reporte_healthanalytics_${new Date().toISOString().slice(0, 10)}${EXTENSION_MAP[format]}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    setTimeout(() => window.URL.revokeObjectURL(objectUrl), 10000);

    result.className = 'mt-3 alert alert-success';
    result.innerHTML = `<i class="bi bi-check-circle me-2"></i>Reporte descargado correctamente (${format.toUpperCase()})`;
    result.classList.remove('d-none');
  } catch (err) {
    result.className = 'mt-3 alert alert-danger';
    result.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i>${err.message}`;
    result.classList.remove('d-none');
  } finally {
    btnText.innerHTML = '<i class="bi bi-download me-2"></i>Descargar Reporte';
    btnSpin.classList.add('d-none');
    btnExp.disabled = false;
  }
}

function initReportes() {
  document.getElementById('btn-exportar').addEventListener('click', exportarReporte);

  document.querySelectorAll('.reporte-format-card').forEach(card => {
    card.addEventListener('click', () => {
      const radio = card.querySelector('input[type=radio]');
      if (radio) radio.checked = true;
    });
  });
}
