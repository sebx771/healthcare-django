/**
 * app.js — Controlador Principal de la SPA
 * HealthAnalytics IPS
 *
 * Gestiona:
 *  - Inicialización y rutas de vistas
 *  - Eventos de autenticación (login / logout)
 *  - Sidebar (toggle móvil, navegación activa)
 *  - Reloj en tiempo real
 *  - Toast de notificaciones globales
 */

(function () {
  'use strict';

  // ── CONFIGURACIÓN DE VISTAS ──────────────────────────────────────
  const VIEWS = {
    dashboard: {
      title:     'Dashboard',
      breadcrumb:'Dashboard',
      module:    () => window.DashboardModule?.render(),
    },
    pacientes: {
      title:     'Pacientes',
      breadcrumb:'Pacientes',
      module:    () => window.PacientesModule?.render(),
    },
    etl: {
      title:     'Panel ETL',
      breadcrumb:'ETL',
      module:    () => window.EtlModule?.render(),
    },
    reportes: {
      title:     'Reportes',
      breadcrumb:'Reportes',
      module:    () => window.ReportesModule?.render(),
    },
    ml: {
      title:     'Predicción ML',
      breadcrumb:'ML',
      module:    () => window.MlModule?.render(),
    },
  };

  let _activeView = 'dashboard';

  // ── ELEMENTOS DEL DOM ────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);

  const els = {
    loginScreen:      $('login-screen'),
    app:              $('app'),
    mainContent:      $('main-content'),
    viewLoader:       $('view-loader'),
    pageTitle:        $('page-title'),
    breadcrumbCurrent:$('breadcrumb-current'),
    sidebar:          $('sidebar'),
    sidebarToggle:    $('sidebar-toggle'),
    sidebarClose:     $('sidebar-close'),
    sidebarOverlay:   $('sidebar-overlay'),
    btnLogout:        $('btn-logout'),
    topbarClock:      $('topbar-clock'),
    sidebarUserName:  $('sidebar-user-name'),
    sidebarUserRole:  $('sidebar-user-role'),
    userAvatarInitials: $('user-avatar-initials'),
    apiStatus:        $('api-status'),
    globalToast:      $('global-toast'),
    toastMessage:     $('toast-message'),
  };

  // ── RELOJ ────────────────────────────────────────────────────────
  function _startClock() {
    const update = () => {
      if (els.topbarClock) {
        els.topbarClock.textContent = new Date().toLocaleTimeString('es-CO', {
          hour:   '2-digit',
          minute: '2-digit',
          second: '2-digit',
        });
      }
    };
    update();
    setInterval(update, 1000);
  }

  // ── TOAST GLOBAL ─────────────────────────────────────────────────
  function showToast(message, type = 'info') {
    const toast = els.globalToast;
    const msg   = els.toastMessage;
    if (!toast || !msg) return;

    // Resetear clases de tipo previas
    toast.className = 'toast align-items-center border-0';
    toast.classList.add(`toast--${type}`);
    msg.textContent = message;

    const bsToast = bootstrap.Toast.getOrCreateInstance(toast, { delay: 4000 });
    bsToast.show();
  }

  window.showToast = showToast;

  // ── NAVEGACIÓN DE VISTAS ─────────────────────────────────────────
  function navigateTo(viewKey) {
    if (!VIEWS[viewKey]) viewKey = 'dashboard';
    _activeView = viewKey;

    const view = VIEWS[viewKey];

    // Actualizar título y breadcrumb
    if (els.pageTitle)         els.pageTitle.textContent         = view.title;
    if (els.breadcrumbCurrent) els.breadcrumbCurrent.textContent = view.breadcrumb;
    document.title = `${view.title} — HealthAnalytics IPS`;

    // Marcar enlace activo en el sidebar
    document.querySelectorAll('.sidebar-link[data-view]').forEach(link => {
      link.classList.toggle('active', link.dataset.view === viewKey);
    });

    // Mostrar loader brevemente, luego renderizar
    if (els.mainContent) {
      els.mainContent.innerHTML = '';
      if (els.viewLoader) els.viewLoader.classList.remove('d-none');

      requestAnimationFrame(() => {
        const html = view.module?.() ?? _placeholderHTML(view.title);
        if (els.viewLoader) els.viewLoader.classList.add('d-none');
        els.mainContent.innerHTML = html;
      });
    }

    // Cerrar sidebar en móvil al navegar
    _closeSidebar();
  }

  function _placeholderHTML(title) {
    return `
    <div class="view-enter view-placeholder">
      <i class="bi bi-hourglass-split view-placeholder__icon"></i>
      <h2 class="view-placeholder__title">${title}</h2>
      <p class="view-placeholder__desc">Este módulo aún no está disponible.</p>
    </div>`;
  }

  // ── SIDEBAR MÓVIL ────────────────────────────────────────────────
  function _openSidebar() {
    els.sidebar?.classList.add('sidebar--open');
    els.sidebarOverlay?.classList.remove('d-none');
    document.body.style.overflow = 'hidden';
  }

  function _closeSidebar() {
    els.sidebar?.classList.remove('sidebar--open');
    els.sidebarOverlay?.classList.add('d-none');
    document.body.style.overflow = '';
  }

  // ── PERFIL EN SIDEBAR ─────────────────────────────────────────────
  function _updateSidebarProfile() {
    const user = window.Auth?.getUser();
    if (!user) return;

    if (els.sidebarUserName)    els.sidebarUserName.textContent = user.username || 'Usuario';
    if (els.sidebarUserRole)    els.sidebarUserRole.textContent = user.rol       || '';
    if (els.userAvatarInitials) {
      const initials = (user.username || 'U')
        .split('.')
        .map(p => p[0]?.toUpperCase() || '')
        .join('')
        .slice(0, 2);
      els.userAvatarInitials.textContent = initials || 'U';
    }
  }

  // ── TRANSICIÓN LOGIN <-> APP ──────────────────────────────────────
  function _showApp() {
    els.loginScreen?.classList.add('d-none');
    els.app?.classList.remove('d-none');
    _updateSidebarProfile();
    navigateTo('dashboard');
    showToast('Sesión iniciada correctamente.', 'success');
  }

  function _showLogin() {
    els.app?.classList.add('d-none');
    els.loginScreen?.classList.remove('d-none');
    // Limpiar el formulario
    const userInput = $('login-username');
    const passInput = $('login-password');
    if (userInput) userInput.value = '';
    if (passInput) passInput.value = '';
    $('login-error')?.classList.add('d-none');
  }

  // ── EVENTOS ───────────────────────────────────────────────────────
  function _bindEvents() {
    // Navegación del sidebar
    document.querySelectorAll('.sidebar-link[data-view]').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        navigateTo(link.dataset.view);
      });
    });

    // Toggle sidebar móvil
    els.sidebarToggle?.addEventListener('click', _openSidebar);
    els.sidebarClose?.addEventListener('click',  _closeSidebar);
    els.sidebarOverlay?.addEventListener('click', _closeSidebar);

    // Cerrar sesión
    els.btnLogout?.addEventListener('click', () => {
      window.Auth?.logout();
    });

    // Eventos de autenticación
    window.addEventListener('auth:login',  _showApp);
    window.addEventListener('auth:logout', _showLogin);
  }

  // ── INICIALIZACIÓN ────────────────────────────────────────────────
  function _init() {
    _startClock();
    _bindEvents();
    window.Auth?.init();

    // Verificar sesión existente al cargar
    if (window.Auth?.isLogged()) {
      _showApp();
    } else {
      _showLogin();
    }
  }

  // Arrancar cuando el DOM esté listo
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }

})();