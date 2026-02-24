/**
 * workflow.js – start button, SSE log streaming, progress bar.
 */

const Workflow = {
  currentRunId: null,
  eventSource: null,
  lastEventId: 0,
  statusPoller: null,

  _apiUrl(path) {
    return API_BASE_URL + path;
  },

  init() {
    document.getElementById('start-btn').addEventListener('click', () => this.start());
    document.getElementById('clear-log-btn').addEventListener('click', () => this.clearLog());
    this._checkRunningStatus();
  },

  // ── Status check on page load ──────────────────────────────────

  async _checkRunningStatus() {
    try {
      const res = await fetch(this._apiUrl('/api/workflow/status')).then(r => r.json());
      if (res.status === 'running') {
        this._setRunning(res.run_id, res.total, res.success, res.failed);
        this._connectSSE(res.run_id, this.lastEventId);
      }
    } catch (_) {}
  },

  // ── Start workflow ─────────────────────────────────────────────

  async start() {
    try {
      const res = await fetch(this._apiUrl('/api/workflow/start'), { method: 'POST' });
      const data = await res.json();
      if (!res.ok) {
        App.toast(data.error || '启动失败', 'error');
        return;
      }
      this.clearLog();
      this._setRunning(data.run_id);
      this._connectSSE(data.run_id, 0);
    } catch (e) {
      App.toast('启动失败：' + e.message, 'error');
    }
  },

  // ── SSE connection ─────────────────────────────────────────────

  _connectSSE(runId, afterId = 0) {
    this.currentRunId = runId;
    if (this.eventSource) this.eventSource.close();

    const url = this._apiUrl(`/api/logs/stream?run_id=${encodeURIComponent(runId)}&after_id=${afterId}`);
    this.eventSource = new EventSource(url);

    this.eventSource.onmessage = (e) => {
      const event = JSON.parse(e.data);
      if (e.lastEventId) this.lastEventId = parseInt(e.lastEventId, 10);
      this._appendLog(event);

      if (event.level === 'progress') {
        const match = event.message.match(/\[(\d+)\/(\d+)\]/);
        if (match) this._updateProgress(parseInt(match[1]), parseInt(match[2]));
      }
    };

    // "done" event: workflow finished
    this.eventSource.addEventListener('done', () => {
      this.eventSource.close();
      this.eventSource = null;
      this._stopPolling();
      this._setIdle('已完成', 'success');
    });

    this.eventSource.onerror = () => {
      // Reconnect logic handled by EventSource automatically,
      // but also poll server status as a fallback
      this._startPolling();
    };

    this._startPolling();
  },

  // ── Status polling (fallback) ──────────────────────────────────

  _startPolling() {
    if (this.statusPoller) return;
    this.statusPoller = setInterval(() => this._pollStatus(), 3000);
  },

  _stopPolling() {
    if (this.statusPoller) {
      clearInterval(this.statusPoller);
      this.statusPoller = null;
    }
  },

  async _pollStatus() {
    try {
      const res = await fetch(this._apiUrl('/api/workflow/status')).then(r => r.json());
      if (res.status === 'idle') {
        this._stopPolling();
        if (this.eventSource) { this.eventSource.close(); this.eventSource = null; }
        this._setIdle('已完成', 'success');
      } else if (res.status === 'running') {
        this._updateProgress(res.success + res.failed, res.total);
      }
    } catch (_) {}
  },

  // ── UI helpers ─────────────────────────────────────────────────

  _setRunning(runId, total = 0, success = 0, failed = 0) {
    this.currentRunId = runId;
    document.getElementById('start-btn').disabled = true;
    document.getElementById('start-btn').textContent = '运行中…';
    document.getElementById('status-dot').className = 'status-dot running';
    document.getElementById('status-text').textContent = '运行中';
    document.getElementById('progress-container').style.display = 'flex';
    if (total > 0) this._updateProgress(success + failed, total);
  },

  _setIdle(label = '空闲', dotClass = 'idle') {
    this.currentRunId = null;
    const btn = document.getElementById('start-btn');
    btn.disabled = false;
    btn.textContent = '▶ 开始运行';
    document.getElementById('status-dot').className = `status-dot ${dotClass}`;
    document.getElementById('status-text').textContent = label;
  },

  _updateProgress(current, total) {
    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    document.getElementById('progress-fill').style.width = pct + '%';
    document.getElementById('progress-text').textContent = `${current} / ${total}`;
  },

  _appendLog(event) {
    const container = document.getElementById('log-output');

    // Remove placeholder on first real log
    const placeholder = container.querySelector('.log-line .log-msg[style]');
    if (placeholder) placeholder.closest('.log-line').remove();

    const line = document.createElement('div');
    line.className = `log-line log-${event.level || 'info'}`;

    const ts = event.ts
      ? new Date(event.ts).toLocaleTimeString('zh-CN', { hour12: false })
      : '';

    line.innerHTML =
      `<span class="log-ts">[${ts}]</span>` +
      `<span class="log-msg">${App.escapeHtml(event.message)}</span>`;

    container.appendChild(line);
    container.scrollTop = container.scrollHeight;
  },

  clearLog() {
    document.getElementById('log-output').innerHTML = '';
    document.getElementById('progress-fill').style.width = '0%';
    document.getElementById('progress-text').textContent = '0 / 0';
    document.getElementById('progress-container').style.display = 'none';
    this._setIdle();
  },
};
