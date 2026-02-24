/**
 * settings.js – AI config form, Google OAuth, XHS Cookie capture.
 */

const Settings = {
  _cookiePoller: null,
  _cookieTimeout: null,

  async init() {
    await this._loadConfig();
    await this.checkGoogleStatus();
    await this._checkCookieStatus();
    this._bindEvents();
  },

  async refresh() {
    await this._loadConfig();
    await this.checkGoogleStatus();
    await this._checkCookieStatus();
  },

  _bindEvents() {
    document.getElementById('save-ai-btn').addEventListener('click', () => this._saveAI());
    document.getElementById('save-sheets-btn').addEventListener('click', () => this._saveSheets());
    document.getElementById('google-auth-btn').addEventListener('click', () => this._startGoogleAuth());
    document.getElementById('capture-cookie-btn').addEventListener('click', () => this._captureCookie());
    document.getElementById('cancel-cookie-btn').addEventListener('click', () => this._cancelCapture());
  },

  // ── Load / save config ─────────────────────────────────────────

  async _loadConfig() {
    try {
      const cfg = await fetch('/api/config').then(r => r.json());
      document.getElementById('ai-provider').value = cfg.ai_provider || '';
      document.getElementById('ai-model').value    = cfg.ai_model    || '';
      document.getElementById('ai-base-url').value = cfg.ai_base_url || '';
      document.getElementById('ai-api-key').value  = '';  // never pre-fill password

      const hint = document.getElementById('ai-key-hint');
      if (cfg.ai_api_key_set) {
        hint.style.display = 'block';
        hint.textContent   = `已保存的 API Key：${cfg.ai_api_key_masked}`;
      } else {
        hint.style.display = 'none';
      }

      document.getElementById('sheets-id').value = cfg.sheets_id || '';
    } catch (_) {}
  },

  async _saveAI() {
    const payload = {
      ai_provider:  document.getElementById('ai-provider').value.trim(),
      ai_model:     document.getElementById('ai-model').value.trim(),
      ai_base_url:  document.getElementById('ai-base-url').value.trim(),
    };
    const key = document.getElementById('ai-api-key').value.trim();
    if (key) payload.ai_api_key = key;

    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    App.toast('AI 配置已保存', 'success');
    await this._loadConfig();  // refresh masked key display
  },

  async _saveSheets() {
    const payload = { sheets_id: document.getElementById('sheets-id').value.trim() };
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    App.toast('Sheets 配置已保存', 'success');
  },

  // ── Google OAuth ───────────────────────────────────────────────

  async checkGoogleStatus() {
    try {
      const status = await fetch('/api/auth/google/status').then(r => r.json());
      const dot  = document.getElementById('google-status-dot');
      const text = document.getElementById('google-status-text');
      const btn  = document.getElementById('google-auth-btn');

      if (status.status === 'authorized') {
        dot.className  = 'status-dot success';
        text.textContent = '已授权';
        btn.textContent  = '重新授权';
      } else if (status.status === 'no_credentials') {
        dot.className  = 'status-dot error';
        text.textContent = status.message;
        btn.disabled   = true;
      } else {
        dot.className  = 'status-dot idle';
        text.textContent = '未授权';
        btn.disabled   = false;
      }
    } catch (_) {}
  },

  async _startGoogleAuth() {
    try {
      const data = await fetch('/api/auth/google').then(r => r.json());
      if (data.auth_url) {
        window.location.href = data.auth_url;
      } else {
        App.toast(data.error || '获取授权链接失败', 'error');
      }
    } catch (e) {
      App.toast('请求失败：' + e.message, 'error');
    }
  },

  // ── XHS Cookie ────────────────────────────────────────────────

  async _checkCookieStatus() {
    try {
      const status = await fetch('/api/cookies/status').then(r => r.json());
      this._renderCookieStatus(status);
    } catch (_) {}
  },

  _renderCookieStatus(status) {
    const dot  = document.getElementById('cookie-status-dot');
    const text = document.getElementById('cookie-status-text');

    switch (status.status) {
      case 'captured':
        dot.className    = 'status-dot success';
        text.textContent = status.message;
        break;
      case 'invalid':
        dot.className    = 'status-dot error';
        text.textContent = '无效，请重新获取';
        break;
      default:
        dot.className    = 'status-dot idle';
        text.textContent = '未获取';
    }
  },

  async _captureCookie() {
    const captureBtn = document.getElementById('capture-cookie-btn');
    const cancelBtn  = document.getElementById('cancel-cookie-btn');
    captureBtn.disabled  = true;
    captureBtn.textContent = '获取中…';
    cancelBtn.style.display = 'inline-flex';

    // Update status to "capturing"
    document.getElementById('cookie-status-dot').className = 'status-dot running';
    document.getElementById('cookie-status-text').textContent = '正在打开浏览器…';

    try {
      await fetch('/api/cookies/capture', { method: 'POST' });
      App.toast('已打开小红书网页，请在弹出的窗口中完成登录', 'info', 6000);
    } catch (e) {
      App.toast('启动失败：' + e.message, 'error');
      this._resetCaptureBtn();
      return;
    }

    // Poll cookie status
    this._cookiePoller = setInterval(async () => {
      try {
        const status = await fetch('/api/cookies/status').then(r => r.json());
        this._renderCookieStatus(status);
        if (status.status === 'captured') {
          this._stopCookiePoller();
          this._resetCaptureBtn();
          App.toast('Cookie 获取成功！', 'success');
        }
      } catch (_) {}
    }, 2000);

    // Timeout after 6 minutes
    this._cookieTimeout = setTimeout(() => {
      this._stopCookiePoller();
      this._resetCaptureBtn();
      App.toast('Cookie 获取超时，请重试', 'warn');
    }, 360_000);
  },

  async _cancelCapture() {
    this._stopCookiePoller();
    this._resetCaptureBtn();
    try {
      await fetch('/api/cookies/cancel', { method: 'POST' });
    } catch (_) {}
    await this._checkCookieStatus();
  },

  _stopCookiePoller() {
    if (this._cookiePoller)  { clearInterval(this._cookiePoller);  this._cookiePoller  = null; }
    if (this._cookieTimeout) { clearTimeout(this._cookieTimeout);   this._cookieTimeout = null; }
  },

  _resetCaptureBtn() {
    const captureBtn = document.getElementById('capture-cookie-btn');
    const cancelBtn  = document.getElementById('cancel-cookie-btn');
    captureBtn.disabled   = false;
    captureBtn.textContent = '获取 Cookie';
    cancelBtn.style.display = 'none';
  },
};
