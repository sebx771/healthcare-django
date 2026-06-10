/**
 * auth.js — Módulo de Autenticación
 * HealthAnalytics IPS
 *
 * Etapa 1: Enlaza el formulario de login y expone helpers de sesión.
 * Etapa 2 completará el control de vistas por roles.
 */

const Auth = (() => {
  // ── ESTADO ──────────────────────────────────────────────────────
  let _currentUser = null;

  // ── PERSISTENCIA ────────────────────────────────────────────────
  function saveUser(userData) {
    _currentUser = userData;
    localStorage.setItem('user_data', JSON.stringify(userData));
  }

  function loadUser() {
    try {
      const raw = localStorage.getItem('user_data');
      _currentUser = raw ? JSON.parse(raw) : null;
    } catch (_) {
      _currentUser = null;
    }
    return _currentUser;
  }

  function getUser()  { return _currentUser || loadUser(); }
  function getRol()   { return getUser()?.rol || null; }
  function isLogged() { return !!window.TokenStore?.getAccess() && !!getUser(); }

  // ── LOGIN ────────────────────────────────────────────────────────
  async function login(username, password) {
    const data = await window.API.AuthAPI.login(username, password);
    window.TokenStore.setTokens(data.access, data.refresh);
    saveUser({ username, rol: data.rol });
    return data;
  }

  // ── LOGOUT ───────────────────────────────────────────────────────
  function logout() {
    window.TokenStore.clear();
    _currentUser = null;
    window.dispatchEvent(new CustomEvent('auth:logout'));
  }

  // ── ENLACE AL FORMULARIO ─────────────────────────────────────────
  function _bindLoginForm() {
    const btnLogin      = document.getElementById('btn-login');
    const inputUser     = document.getElementById('login-username');
    const inputPass     = document.getElementById('login-password');
    const errorDiv      = document.getElementById('login-error');
    const errorMsg      = document.getElementById('login-error-msg');
    const btnText       = document.getElementById('login-btn-text');
    const spinner       = document.getElementById('login-spinner');
    const togglePassBtn = document.getElementById('toggle-password');
    const toggleIcon    = document.getElementById('toggle-icon');

    // Mostrar/ocultar contraseña
    togglePassBtn?.addEventListener('click', () => {
      const isPassword = inputPass.type === 'password';
      inputPass.type   = isPassword ? 'text' : 'password';
      toggleIcon.className = isPassword ? 'bi bi-eye-slash' : 'bi bi-eye';
    });

    // Permitir Enter en el formulario
    [inputUser, inputPass].forEach(el =>
      el?.addEventListener('keydown', e => {
        if (e.key === 'Enter') btnLogin?.click();
      })
    );

    btnLogin?.addEventListener('click', async () => {
      const username = inputUser?.value.trim();
      const password = inputPass?.value.trim();

      // Validación básica
      if (!username || !password) {
        _showLoginError('Por favor completa todos los campos.');
        return;
      }

      // Estado de carga
      _setLoginLoading(true, btnText, spinner, btnLogin);
      errorDiv.classList.add('d-none');

      try {
        await login(username, password);
        window.dispatchEvent(new CustomEvent('auth:login'));
      } catch (err) {
        const msg = err.status === 401
          ? 'Credenciales incorrectas. Verifica tu usuario y contraseña.'
          : err.message || 'Error de conexión con el servidor.';
        _showLoginError(msg, errorMsg, errorDiv);
        inputPass.value = '';
        inputPass.focus();
      } finally {
        _setLoginLoading(false, btnText, spinner, btnLogin);
      }
    });
  }

  function _showLoginError(msg, msgEl, divEl) {
    const errMsg = msgEl || document.getElementById('login-error-msg');
    const errDiv = divEl || document.getElementById('login-error');
    if (errMsg) errMsg.textContent = msg;
    errDiv?.classList.remove('d-none');
  }

  function _setLoginLoading(loading, btnText, spinner, btn) {
    if (btnText)  btnText.textContent = loading ? 'Verificando...' : 'Ingresar';
    if (spinner)  spinner.classList.toggle('d-none', !loading);
    if (btn)      btn.disabled = loading;
  }

  // ── INIT ──────────────────────────────────────────────────────────
  function init() {
    _bindLoginForm();
  }

  return { init, login, logout, getUser, getRol, isLogged };
})();

window.Auth = Auth;