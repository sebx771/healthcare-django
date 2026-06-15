const API_BASE_URL = 'http://localhost:8000';

async function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem('access_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const response = await fetch(`${API_BASE_URL}${url}`, { ...options, headers });

  if (response.status === 401) {
    const refreshed = await refreshToken();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${localStorage.getItem('access_token')}`;
      return fetch(`${API_BASE_URL}${url}`, { ...options, headers });
    } else {
      logout();
      throw new Error('Sesión expirada');
    }
  }
  return response;
}

async function refreshToken() {
  const refresh = localStorage.getItem('refresh_token');
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    if (data.access) {
      localStorage.setItem('access_token', data.access);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('rol');
  localStorage.removeItem('username');
  window.showLogin();
}

function setLoginLoading(isLoading) {
  const form = document.getElementById('form-login');
  const btnText = document.getElementById('btn-login-text');
  const btnSpinner = document.getElementById('btn-login-spinner');
  const submitBtn = form ? form.querySelector('button[type=submit]') : null;

  if (btnText) btnText.textContent = isLoading ? 'Verificando...' : 'Iniciar Sesión';
  if (btnSpinner) btnSpinner.classList.toggle('d-none', !isLoading);
  if (submitBtn) submitBtn.disabled = isLoading;
}

function showLoginError(message) {
  const errorDiv = document.getElementById('login-error');
  if (!errorDiv) return;
  errorDiv.textContent = message;
  errorDiv.classList.remove('d-none');
}

function getLoginTokens(data) {
  if (!data || typeof data !== 'object') return null;

  const access = data.access_token || data.access || '';
  const refresh = data.refresh_token || data.refresh || '';

  if (!access || !refresh) return null;

  return { access, refresh };
}

function initAuth() {
  const form = document.getElementById('form-login');
  if (!form) return;

  const togglePwd = document.getElementById('toggle-password');
  const pwdInput = document.getElementById('login-password');

  if (togglePwd && pwdInput) {
    togglePwd.addEventListener('click', () => {
      const isText = pwdInput.type === 'text';
      pwdInput.type = isText ? 'password' : 'text';
      togglePwd.querySelector('i').className = isText ? 'bi bi-eye' : 'bi bi-eye-slash';
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    showLoginError('');
    setLoginLoading(true);

    try {
      const username = document.getElementById('login-username').value.trim();
      const password = document.getElementById('login-password').value;

      if (!username || !password) {
        throw new Error('Credenciales inválidas');
      }

      const res = await fetch(`${API_BASE_URL}/api/auth/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        await res.json().catch(() => ({}));
        throw new Error('Credenciales inválidas');
      }

      const data = await res.json().catch(() => null);
      const tokens = getLoginTokens(data);

      if (!tokens) {
        throw new Error('Credenciales inválidas');
      }

      localStorage.setItem('access_token', tokens.access);
      localStorage.setItem('refresh_token', tokens.refresh);
      localStorage.setItem('rol', data.rol || data.role || 'Médico');
      localStorage.setItem('username', data.username || username);

      window.showApp();
    } catch (err) {
      showLoginError(err.message || 'No se pudo iniciar sesión. Verifique sus credenciales o intente nuevamente.');
      window.showLogin();
    } finally {
      setLoginLoading(false);
    }
  });
}

document.addEventListener('DOMContentLoaded', initAuth);
