# Development Log

## v1.1.0 – 飞书多维表格迁移

**记录时间**：2026-02-25
**版本号**：v1.1.0
**状态**：已迁移，README 已同步更新

### 变更摘要

- 从 Google Sheets 迁移到飞书多维表格（Feishu Sheets）
- 移除 Google OAuth 2.0 授权流程，改用飞书 App ID + App Secret
- 所有表格 API 调用改为异步（httpx），简化代码
- 前端设置页面更新：Google 授权 → 飞书配置（App ID、App Secret、测试连接）
- 更新 README.md 文档，同步飞书配置说明

### 文件变更

| 文件 | 变更 |
|------|------|
| `app/services/sheets_service.py` | 完全重写，使用飞书 API (httpx 异步) |
| `app/services/workflow_service.py` | 移除 `asyncio.to_thread()` 包装器，更新错误提示 |
| `app/api/auth.py` | 移除 Google OAuth，添加 `/api/auth/feishu/status` |
| `app/api/config_api.py` | 添加 `feishu_app_id`、`feishu_app_secret` 字段，支持脱敏显示 |
| `config.py` | 移除 Google 相关常量 (CREDENTIALS_PATH, TOKEN_PATH, GOOGLE_SCOPES) |
| `requirements.txt` | 移除 `google-auth-oauthlib`, `google-api-python-client`, `google-auth-httplib2` |
| `frontend/index.html` | Google Sheets 表单 → 飞书多维表格配置表单 |
| `frontend/js/settings.js` | Google OAuth 流程 → 飞书连接测试与保存 |
| `README.md` | 更新安装步骤、配置说明、FAQ，移除 Google 相关引用 |

### 飞书配置步骤

1. 访问 [飞书开放平台](https://open.feishu.cn/app/)
2. 创建「企业自建应用」
3. 启用权限：
   - `drive:drive:readonly`（读取多维表格）
   - `sheets:spreadsheet:readonly`（读取工作表）
   - `sheets:spreadsheet:write`（写入工作表）
4. 发布应用（或添加测试用户）
5. 在设置页面填写：App ID、App Secret、多维表格 ID

---

## v1.0.0 – 初始构建

**记录时间**：2026-02-24
**版本号**：v1.0.0
**状态**：构建完成，待安装依赖并首次运行

---

## 项目结构（33个文件）

```
xhslink_260224/
├── run.py                    ← 启动入口
├── config.py                 ← 全局配置（路径、端口、列映射）
├── requirements.txt
├── README.md
├── app/
│   ├── main.py               ← FastAPI 应用
│   ├── api/                  ← 所有 HTTP 路由
│   │   ├── workflow.py       ← POST /api/workflow/start
│   │   ├── logs.py           ← GET /api/logs/stream (SSE)
│   │   ├── history.py        ← 历史记录查询
│   │   ├── config_api.py     ← 配置读写
│   │   ├── cookies.py        ← XHS Cookie 管理
│   │   └── auth.py           ← Google OAuth2
│   ├── services/             ← 业务逻辑
│   │   ├── workflow_service.py
│   │   ├── xhs_scraper.py    ← Playwright 爬虫
│   │   ├── sheets_service.py ← Google Sheets 读写
│   │   ├── ai_service.py     ← 图片/视频/总结 AI
│   │   └── sse_manager.py    ← 实时日志推送
│   └── db/                   ← SQLite 数据层
└── frontend/                 ← 纯 HTML + JS UI
    ├── index.html
    ├── css/style.css
    └── js/{app,workflow,settings,history}.js
```

---

## 技术选型

| 层次 | 技术 |
|------|------|
| 后端框架 | Python + FastAPI + uvicorn |
| 浏览器爬取 | Playwright（chromium，headless + headful 两种模式） |
| 在线表格 | 飞书多维表格 API（App ID + App Secret） |
| AI 调用 | openai SDK（OpenAI 兼容接口，支持所有主流厂商） |
| 本地存储 | SQLite（aiosqlite 异步） |
| 实时日志 | SSE（Server-Sent Events） |
| 前端 | 纯 HTML + Vanilla JS，FastAPI 静态文件服务 |

---

## 启动方式

```bash
pip install -r requirements.txt
playwright install chromium
python run.py
```

浏览器自动打开 `http://localhost:8000`。

---

## 首次使用三步配置

1. **设置 → 小红书 Cookie**：点击「获取 Cookie」→ 在弹出浏览器中登录小红书
2. **设置 → AI 模型**：填写模型厂商、名称（推荐 `gemini-2.0-flash`）和 API Key
3. **设置 → 飞书多维表格**：在飞书开放平台创建应用获取 App ID 和 App Secret，填写到设置页面

配置完成后，在 Sheets A 列填写小红书链接，点击「▶ 开始运行」即可。

---

## Google Sheets 列顺序（严格固定）

| 列 | 字段 | 说明 |
|----|------|------|
| A | link | 用户填入的小红书链接 |
| B | title | 笔记标题 |
| C | author | 作者昵称 |
| D | date | 发布时间 |
| E | stars | 收藏量 |
| F | text_original | 笔记正文 |
| G | pic_url_list | 图片地址列表 |
| H | video_url_list | 视频地址列表 |
| I | pic_processed | AI 图片解析内容 |
| J | video_processed | AI 视频解析内容 |
| K | summary | AI 综合总结 |
| L | auto | 完成标记（1=完成，空=待处理） |
| M | error | 错误原因（空=无错误） |

---

## API 端点一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/workflow/start | 启动工作流，返回 run_id |
| GET  | /api/workflow/status | 当前工作流状态 |
| GET  | /api/logs/stream?run_id=X&after_id=N | SSE 实时日志流 |
| GET  | /api/history | 历史运行列表 |
| GET  | /api/history/{run_id} | 单次运行详情 + 完整日志 |
| GET  | /api/config | 读取配置（API Key 脱敏返回） |
| POST | /api/config | 保存配置 |
| GET  | /api/auth/feishu/status | 飞书授权状态 |
| GET  | /api/cookies/status | XHS Cookie 状态 |
| POST | /api/cookies/capture | 打开浏览器让用户登录 XHS |
| POST | /api/cookies/cancel | 取消 Cookie 捕获 |

---

## SQLite 数据库 Schema

```sql
-- 配置表（key-value）
CREATE TABLE config (key TEXT PRIMARY KEY, value TEXT);
-- 存储 key：ai_provider, ai_model, ai_base_url, ai_api_key, sheets_id, feishu_app_id, feishu_app_secret

-- 运行记录
CREATE TABLE runs (
    id TEXT PRIMARY KEY, started_at TEXT, completed_at TEXT,
    status TEXT, total INTEGER, success INTEGER, failed INTEGER
);

-- 运行事件日志
CREATE TABLE run_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT, ts TEXT, level TEXT, message TEXT
);
```

---

## 核心工作流时序（F1–F9）

```
用户点击「开始运行」
  ↓
F1  读取飞书多维表格，筛选 auto='' 且 error='' 的行
  ↓
对每条链接（串行）：
  F4  Playwright 抓取笔记数据（携带 XHS Cookie）
  F5  AI 解析图片 → pic_processed
  F6  AI 解析视频 → video_processed
  F7  AI 生成总结 → summary
  F8  实时回写飞书多维表格（空值占位为 "0"）
  F9  更新状态：成功 auto=1，失败 error=失败原因
  ↓
网页端展示完成摘要，历史记录保存至 SQLite
```
