/**
 * history.js – list past workflow runs and expand log details.
 */

const History = {
  init() {
    // Lazy load on tab switch via App.switchTab
  },

  async load() {
    const container = document.getElementById('history-list');
    container.innerHTML = '<p class="loading-text">加载中…</p>';

    try {
      const data = await fetch('/api/history').then(r => r.json());
      const runs = data.runs || [];

      if (runs.length === 0) {
        container.innerHTML = '<p class="empty">暂无历史记录</p>';
        return;
      }

      container.innerHTML = runs.map(run => `
        <div class="history-item" id="run-${run.id}">
          <div class="history-header" onclick="History.toggle('${run.id}')">
            <div class="history-meta">
              <span class="history-time">${this._fmtDate(run.started_at)}</span>
              <span class="status-badge status-${run.status}">
                ${this._statusLabel(run.status)}
              </span>
            </div>
            <div class="history-stats">
              <span class="stat success">✓ ${run.success}</span>
              <span class="stat error">✗ ${run.failed}</span>
              <span class="stat">共 ${run.total} 条</span>
            </div>
          </div>
          <div class="history-events" id="events-${run.id}" style="display:none"></div>
        </div>
      `).join('');

    } catch (e) {
      container.innerHTML = `<p class="empty">加载失败：${App.escapeHtml(e.message)}</p>`;
    }
  },

  async toggle(runId) {
    const eventsEl = document.getElementById(`events-${runId}`);
    if (!eventsEl) return;

    const isHidden = eventsEl.style.display === 'none';
    eventsEl.style.display = isHidden ? 'block' : 'none';

    if (isHidden && !eventsEl.dataset.loaded) {
      await this._loadEvents(runId, eventsEl);
      eventsEl.dataset.loaded = '1';
    }
  },

  async _loadEvents(runId, container) {
    container.innerHTML = '<p class="loading-text" style="color:#555">加载中…</p>';
    try {
      const data = await fetch(`/api/history/${encodeURIComponent(runId)}`).then(r => r.json());
      const events = data.events || [];

      if (events.length === 0) {
        container.innerHTML = '<p class="loading-text" style="color:#555">无日志记录</p>';
        return;
      }

      container.innerHTML = events.map(e => `
        <div class="log-line log-${e.level}">
          <span class="log-ts">[${this._fmtTime(e.ts)}]</span>
          <span class="log-msg">${App.escapeHtml(e.message)}</span>
        </div>
      `).join('');

    } catch (err) {
      container.innerHTML = `<p class="loading-text" style="color:#f87171">加载失败</p>`;
    }
  },

  _fmtDate(iso) {
    try {
      return new Date(iso).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        hour12: false,
      });
    } catch (_) { return iso; }
  },

  _fmtTime(iso) {
    try {
      return new Date(iso).toLocaleTimeString('zh-CN', { hour12: false });
    } catch (_) { return iso; }
  },

  _statusLabel(s) {
    return { running: '运行中', completed: '已完成', failed: '失败' }[s] || s;
  },
};
