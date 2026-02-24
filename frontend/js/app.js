/**
 * app.js – tab switching, toast notifications, URL param handling.
 * All other modules (Settings, Workflow, History) register themselves on
 * DOMContentLoaded and expose a public init() method.
 */

const App = {
  currentTab: 'console',

  init() {
    this._setupTabs();
    this._handleUrlParams();
  },

  _setupTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
    });
  },

  switchTab(tab) {
    this.currentTab = tab;
    document.querySelectorAll('.tab-btn').forEach(b =>
      b.classList.toggle('active', b.dataset.tab === tab)
    );
    document.querySelectorAll('.tab-content').forEach(c =>
      c.classList.toggle('active', c.id === `tab-${tab}`)
    );
    if (tab === 'history') History.load();
    if (tab === 'settings') Settings.refresh();
  },

  _handleUrlParams() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('auth_success')) {
      history.replaceState({}, '', '/');
      this.switchTab('settings');
      Settings.checkGoogleStatus();
      this.toast('Google Sheets 授权成功！', 'success');
    } else if (params.get('auth_error')) {
      history.replaceState({}, '', '/');
      this.switchTab('settings');
      this.toast('Google 授权失败：' + decodeURIComponent(params.get('auth_error')), 'error');
    }
  },

  toast(msg, type = 'info', duration = 4000) {
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), duration);
  },

  escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  },
};

document.addEventListener('DOMContentLoaded', () => {
  App.init();
  Settings.init();
  Workflow.init();
  History.init();
});
