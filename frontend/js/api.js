/**
 * api.js — Capa centralizada de comunicación con la API REST
 * HealthAnalytics IPS
 *
 * Todos los módulos importan sus llamadas desde aquí.
 * La URL base se ajusta según el entorno detectado.
 */

const API_BASE_URL = (() => {
  // En desarrollo Django corre típicamente en :8000
  if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  // En producción, relativo al mismo origen
  return '';
})();

// ── TOKEN HELPERS ──────────────────────────────────────────────────
const TokenStore = {
  getAccess:   () => localStorage.getItem('access_token'),
  getRefresh:  () => localStorage.getItem('refresh_token'),
  setTokens:   (access, refresh) => {
    localStorage.setItem('access_token',  access);
    if (refresh) localStorage.setItem('refresh_token', refresh);
  },
  clear: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_data');
  },
};

// ── FETCH BASE ─────────────────────────────────────────────────────
/**
 * Realiza una petición HTTP con manejo automático de JWT y errores.
 * @param {string} endpoint  - Ruta relativa al API_BASE_URL  ("/api/...")
 * @param {object} options   - Opciones de fetch (method, body, etc.)
 * @param {boolean} auth     - Si debe incluir el header Authorization
 */
async function apiFetch(endpoint, options = {}, auth = true) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (auth) {
    const token = TokenStore.getAccess();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  const config = { ...options, headers };

  let response = await fetch(`${API_BASE_URL}${endpoint}`, config);

  // Intentar renovar el token si expiró (401)
  if (response.status === 401 && auth) {
    const refreshed = await _refreshAccessToken();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${TokenStore.getAccess()}`;
      response = await fetch(`${API_BASE_URL}${endpoint}`, { ...config, headers });
    } else {
      TokenStore.clear();
      window.dispatchEvent(new CustomEvent('auth:logout'));
      throw new ApiError(401, 'Sesión expirada. Por favor inicia sesión de nuevo.');
    }
  }

  if (!response.ok) {
    let errorMsg = `Error ${response.status}`;
    try {
      const errData = await response.json();
      errorMsg = errData.detail || errData.message || errorMsg;
    } catch (_) { /* ignorar */ }
    throw new ApiError(response.status, errorMsg);
  }

  // Para respuestas sin cuerpo (204)
  if (response.status === 204) return null;

  return response.json();
}

/**
 * Fetch para respuestas binarias (exportaciones, blobs).
 */
async function apiFetchBlob(endpoint, options = {}) {
  const headers = {
    ...(options.headers || {}),
    'Authorization': `Bearer ${TokenStore.getAccess()}`,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });

  if (!response.ok) {
    throw new ApiError(response.status, `Error al exportar (${response.status})`);
  }

  return response.blob();
}

// ── ERROR PERSONALIZADO ────────────────────────────────────────────
class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
    this.name   = 'ApiError';
  }
}

// ── REFRESH DE TOKEN ───────────────────────────────────────────────
async function _refreshAccessToken() {
  const refresh = TokenStore.getRefresh();
  if (!refresh) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });

    if (!response.ok) return false;
    const data = await response.json();
    TokenStore.setTokens(data.access);
    return true;
  } catch (_) {
    return false;
  }
}

// ── ENDPOINTS POR MÓDULO ───────────────────────────────────────────

/** AUTENTICACIÓN */
const AuthAPI = {
  login: (username, password) =>
    apiFetch('/api/auth/login/', {
      method: 'POST',
      body:   JSON.stringify({ username, password }),
    }, false),

  refresh: (refresh) =>
    apiFetch('/api/auth/refresh/', {
      method: 'POST',
      body:   JSON.stringify({ refresh }),
    }, false),
};

/** PACIENTES */
const PacientesAPI = {
  listar: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return apiFetch(`/api/pacientes/${qs ? '?' + qs : ''}`);
  },

  detalle: (id) => apiFetch(`/api/pacientes/${id}/`),

  cargarArchivo: (formData) =>
    apiFetch('/api/pacientes/upload/', {
      method:  'POST',
      headers: {}, // Sin Content-Type para multipart
      body:    formData,
    }),
};

/** ETL */
const EtlAPI = {
  ejecutar: () => apiFetch('/api/etl/run/', { method: 'POST' }),
  historial: ()  => apiFetch('/api/etl/history/'),
};

/** DASHBOARD */
const DashboardAPI = {
  kpis: () => apiFetch('/api/dashboard/kpis/'),
};

/** REPORTES */
const ReportesAPI = {
  /**
   * Descarga un reporte en el formato indicado.
   * @param {'csv'|'excel'|'pdf'} formato
   * @param {object} filtros - { search, riesgo, fecha_desde, fecha_hasta }
   */
  exportar: async (formato, filtros = {}) => {
    const params = new URLSearchParams({ export_format: formato, ...filtros });
    const blob   = await apiFetchBlob(`/api/reportes/export/?${params}`);
    const ext    = formato === 'excel' ? 'xlsx' : formato;
    const url    = window.URL.createObjectURL(blob);
    const a      = document.createElement('a');
    a.href       = url;
    a.download   = `pacientes_${Date.now()}.${ext}`;
    a.click();
    window.URL.revokeObjectURL(url);
  },
};

/** ML */
const MlAPI = {
  predecir: (datos) =>
    apiFetch('/api/ml/prediccion/', {
      method: 'POST',
      body:   JSON.stringify(datos),
    }),
};

// Exponer al ámbito global para uso desde los demás módulos
window.API = { AuthAPI, PacientesAPI, EtlAPI, DashboardAPI, ReportesAPI, MlAPI };
window.TokenStore = TokenStore;
window.ApiError   = ApiError;