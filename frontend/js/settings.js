/**
 * settings.js – AI config form, Feishu connection, XHS Cookie capture.
 */

const Settings = {
  _cookiePoller: null,
  _cookieTimeout: null,

  async init() {
    await this._loadConfig();
    await this._checkFeishuStatus();
    await this._checkCookieStatus();
    this._bindEvents();
  },

  async refresh() {
    await this._loadConfig();
    await this._checkFeishuStatus();
    await this._checkCookieStatus();
  },

  _bindEvents() {
    document.getElementById('save-ai-btn').addEventListener('click', () => this._saveAI());
    document.getElementById('save-feishu-btn').addEventListener('click', () => this._saveFeishu());
    document.getElementById('feishu-test-btn').addEventListener('click', () => this._testFeishu());
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
      document.getElementById('feishu-app-id').value = cfg.feishu_app_id || '';
      document.getElementById('feishu-app-secret').value = '';  // never pre-fill

      const secretHint = document.getElementById('feishu-secret-hint');
      if (cfg.feishu_app_secret_set) {
        secretHint.style.display = 'block';
        secretHint.textContent   = `已保存的 App Secret：${cfg.feishu_app_secret_masked}`;
      } else {
        secretHint.style.display = 'none';
      }
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

  async _saveFeishu() {
    const payload = {
      sheets_id: document.getElementById('sheets-id').value.trim(),
      feishu_app_id: document.getElementById('feishu-app-id').value.trim(),
    };
    const secret = document.getElementById('feishu-app-secret').value.trim();
    if (secret) payload.feishu_app_secret = secret;

    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    App.toast('飞书配置已保存', 'success');
    await this._loadConfig();
    await this._checkFeishuStatus();
  },

  // ── Feishu Connection ──────────────────────────────────────────

  async _checkFeishuStatus() {
    try {
      const status = await fetch('/api/auth/feishu/status').then(r => r.json());
      const dot  = document.getElementById('feishu-status-dot');
      const text = document.getElementById('feishu-status-text');

      if (status.status === 'authorized') {
        dot.className  = 'status-dot success';
        text.textContent = '连接正常';
      } else if (status.status === 'no_credentials') {
        dot.className  = 'status-dot error';
        text.textContent = '未配置';
      } else {
        dot.className  = 'status-dot error';
        text.textContent = '连接失败';
      }
    } catch (_) {
      const dot = document.getElementById('feishu-status-dot');
      const text = document.getElementById('feishu-status-text');
      dot.className = 'status-dot error';
      text.textContent = '检查失败';
    }
  },

  async _testFeishu() {
    const btn = document.getElementById('feishu-test-btn');
    btn.disabled = true;
    btn.textContent = '测试中…';

    try {
      // First save the current values
      await this._saveFeishu();
      // Then test connection
      const status = await fetch('/api/auth/feishu/status').then(r => r.json());

      if (status.status === 'authorized') {
        App.toast('飞书连接测试成功', 'success');
      } else {
        App.toast(status.message || '连接失败', 'error');
      }
      await this._checkFeishuStatus();
    } catch (e) {
      App.toast('测试失败：' + e.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = '测试连接';
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
