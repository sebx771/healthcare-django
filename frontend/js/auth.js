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

function initAuth() {
  const form = document.getElementById('form-login');
  const btnText = document.getElementById('btn-login-text');
  const btnSpinner = document.getElementById('btn-login-spinner');
  const errorDiv = document.getElementById('login-error');
  const togglePwd = document.getElementById('toggle-password');
  const pwdInput = document.getElementById('login-password');

  togglePwd.addEventListener('click', () => {
    const isText = pwdInput.type === 'text';
    pwdInput.type = isText ? 'password' : 'text';
    togglePwd.querySelector('i').className = isText ? 'bi bi-eye' : 'bi bi-eye-slash';
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorDiv.classList.add('d-none');
    btnText.textContent = 'Verificando...';
    btnSpinner.classList.remove('d-none');
    form.querySelector('button[type=submit]').disabled = true;

    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.message || 'Credenciales inválidas');
      }

      const data = await res.json();
      localStorage.setItem('access_token', data.access_token || data.access || '');
      localStorage.setItem('refresh_token', data.refresh_token || data.refresh || '');
      localStorage.setItem('rol', data.rol || data.role || 'Médico');
      localStorage.setItem('username', data.username || username);

      window.showApp();
    } catch (err) {
      errorDiv.textContent = err.message || 'Error al iniciar sesión';
      errorDiv.classList.remove('d-none');
    } finally {
      btnText.textContent = 'Iniciar Sesión';
      btnSpinner.classList.add('d-none');
      form.querySelector('button[type=submit]').disabled = false;
    }
  });
}
