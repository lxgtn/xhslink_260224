/**
 * settings.js – AI config form, Feishu connection, XHS Cookie capture.
 */

const Settings = {
  _formKeys: ['ai-provider', 'ai-model', 'ai-base-url', 'ai-api-key',
              'sheets-id', 'feishu-app-id', 'feishu-app-secret',
              'cookie-input'],

  async init() {
    this._restoreFormFromSession(); // Restore form data before loading config
    await this._loadConfig();
    await this._checkFeishuStatus();
    await this._checkCookieStatus();
    this._bindEvents();
    this._setupFormPersistence();
  },

  async refresh() {
    // Don't reload config if form has been modified (preserve user input)
    const hasSessionData = this._formKeys.some(key => sessionStorage.getItem('form_' + key));
    if (!hasSessionData) {
      await this._loadConfig();
    }
    await this._checkFeishuStatus();
    await this._checkCookieStatus();
  },

  // ── Form persistence using sessionStorage ─────────────────────────

  _setupFormPersistence() {
    // Save form data on input change
    this._formKeys.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', () => {
          sessionStorage.setItem('form_' + id, el.value);
        });
      }
    });
  },

  _restoreFormFromSession() {
    this._formKeys.forEach(id => {
      const el = document.getElementById(id);
      const saved = sessionStorage.getItem('form_' + id);
      if (el && saved) {
        el.value = saved;
      }
    });
  },

  _clearFormSession() {
    this._formKeys.forEach(key => {
      sessionStorage.removeItem('form_' + key);
    });
  },

  _extractSpreadsheetToken(urlOrToken) {
    // Extract spreadsheet token from full Feishu URL or return as-is if already token
    // Supported formats:
    // - https://xxx.feishu.cn/wiki/AbCdEfGh12345678
    // - https://xxx.feishu.cn/base/AbCdEfGh12345678
    // - AbCdEfGh12345678 (direct token)
    const trimmed = urlOrToken.trim();
    if (!trimmed) return '';

    // If it's already just a token (no slashes, no protocol), return as-is
    if (!trimmed.includes('/') && !trimmed.includes(':')) {
      return trimmed;
    }

    // Try to extract token from URL
    try {
      const url = new URL(trimmed);
      // Match /wiki/xxx or /base/xxx patterns
      const match = url.pathname.match(/\/(?:wiki|base)\/([a-zA-Z0-9_-]+)/);
      if (match) {
        return match[1];
      }
    } catch (_) {
      // Not a valid URL, return as-is for backward compatibility
    }

    return trimmed;
  },

  _bindEvents() {
    document.getElementById('save-ai-btn').addEventListener('click', () => this._saveAI());
    document.getElementById('save-feishu-btn').addEventListener('click', () => this._saveFeishu());
    document.getElementById('feishu-test-btn').addEventListener('click', () => this._testFeishu());
    document.getElementById('save-cookie-btn').addEventListener('click', () => this._saveCookie());
    document.getElementById('cancel-cookie-btn').addEventListener('click', () => this._clearCookie());
  },

  // ── Load / save config ─────────────────────────────────────────

  _apiUrl(path) {
    return API_BASE_URL + path;
  },

  async _loadConfig() {
    try {
      const cfg = await fetch(this._apiUrl('/api/config')).then(r => r.json());

      // Only fill empty fields to avoid overwriting user input
      const setIfEmpty = (id, value) => {
        const el = document.getElementById(id);
        if (el && !el.value) el.value = value || '';
      };

      setIfEmpty('ai-provider', cfg.ai_provider);
      setIfEmpty('ai-model', cfg.ai_model);
      setIfEmpty('ai-base-url', cfg.ai_base_url);
      // API Key: never pre-fill, but show hint if saved

      const hint = document.getElementById('ai-key-hint');
      if (cfg.ai_api_key_set) {
        hint.style.display = 'block';
        hint.textContent   = `已保存的 API Key：${cfg.ai_api_key_masked}`;
      } else {
        hint.style.display = 'none';
      }

      setIfEmpty('sheets-id', cfg.sheets_id);
      setIfEmpty('feishu-app-id', cfg.feishu_app_id);
      setIfEmpty('feishu-app-secret', cfg.feishu_app_secret);

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
    const payload = {};
    const provider = document.getElementById('ai-provider').value.trim();
    const model = document.getElementById('ai-model').value.trim();
    const baseUrl = document.getElementById('ai-base-url').value.trim();
    const key = document.getElementById('ai-api-key').value.trim();

    if (provider) payload.ai_provider = provider;
    if (model) payload.ai_model = model;
    if (baseUrl) payload.ai_base_url = baseUrl;
    if (key) payload.ai_api_key = key;

    await fetch(this._apiUrl('/api/config'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    // Clear saved form data for AI fields after successful save
    ['ai-provider', 'ai-model', 'ai-base-url', 'ai-api-key'].forEach(key => {
      sessionStorage.removeItem('form_' + key);
    });

    App.toast('AI 配置已保存', 'success');
    await this._loadConfig();  // refresh masked key display
  },

  async _saveFeishu() {
    const payload = {};
    const sheetsUrl = document.getElementById('sheets-id').value.trim();
    const appId = document.getElementById('feishu-app-id').value.trim();
    const secret = document.getElementById('feishu-app-secret').value.trim();

    // Extract spreadsheet token from URL (or use as-is if already token)
    if (sheetsUrl) {
      const token = this._extractSpreadsheetToken(sheetsUrl);
      if (token) {
        payload.sheets_id = token;
      }
    }
    if (appId) payload.feishu_app_id = appId;
    if (secret) payload.feishu_app_secret = secret;

    await fetch(this._apiUrl('/api/config'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    // Clear saved form data for Feishu fields after successful save
    ['sheets-id', 'feishu-app-id', 'feishu-app-secret'].forEach(key => {
      sessionStorage.removeItem('form_' + key);
    });

    App.toast('飞书配置已保存', 'success');
    await this._loadConfig();
    await this._checkFeishuStatus();
  },

  // ── Feishu Connection ──────────────────────────────────────────

  async _checkFeishuStatus() {
    const testBtn = document.getElementById('feishu-test-btn');
    const statusContainer = document.getElementById('feishu-status-container');
    const dot = document.getElementById('feishu-status-dot');
    const text = document.getElementById('feishu-status-text');

    // Check if we have saved credentials
    const hasCredentials = document.getElementById('feishu-app-id').value.trim() &&
                          document.getElementById('feishu-app-secret').value.trim();

    // Show/hide test button and status based on whether credentials exist
    if (hasCredentials) {
      testBtn.style.display = 'inline-flex';
      statusContainer.style.display = 'flex';
    } else {
      testBtn.style.display = 'none';
      statusContainer.style.display = 'none';
      return; // Don't check status if no credentials
    }

    try {
      const status = await fetch(this._apiUrl('/api/auth/feishu/status')).then(r => r.json());

      if (status.status === 'authorized') {
        dot.className = 'status-dot success';
        text.textContent = '连接正常';
      } else if (status.status === 'no_credentials') {
        dot.className = 'status-dot idle';
        text.textContent = '未配置';
      } else {
        dot.className = 'status-dot error';
        text.textContent = '连接失败';
      }
    } catch (_) {
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
      const status = await fetch(this._apiUrl('/api/auth/feishu/status')).then(r => r.json());

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
      const status = await fetch(this._apiUrl('/api/cookies/status')).then(r => r.json());
      this._renderCookieStatus(status);
    } catch (_) {}

    // Load saved raw cookie string for auto-fill
    try {
      const raw = await fetch(this._apiUrl('/api/cookies/raw')).then(r => r.json());
      const cookieInput = document.getElementById('cookie-input');
      if (raw.cookie_string && cookieInput && !cookieInput.value) {
        cookieInput.value = raw.cookie_string;
      }
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

  // ── Cookie (manual paste) ─────────────────────────────────

  _clearCookie() {
    const input = document.getElementById('cookie-input');
    input.value = '';
    sessionStorage.removeItem('form_cookie-input');
    input.focus();
  },

  async _saveCookie() {
    const cookieString = document.getElementById('cookie-input').value.trim();
    if (!cookieString) {
      App.toast('请输入 Cookie 内容', 'error');
      return;
    }

    const btn = document.getElementById('save-cookie-btn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '保存中…';

    try {
      const res = await fetch(this._apiUrl('/api/cookies/import'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cookie_string: cookieString }),
      });
      const result = await res.json();

      if (result.status === 'error') {
        App.toast(result.message || '保存失败', 'error');
      } else {
        App.toast(result.message, 'success');
        this._renderCookieStatus(result);
        // Clear saved cookie input from sessionStorage after successful save
        sessionStorage.removeItem('form_cookie-input');
      }
    } catch (e) {
      App.toast('保存失败：' + e.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  },
};
