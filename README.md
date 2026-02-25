# XHS Link – 小红书内容聚合工具

基于 Python + FastAPI + Playwright 构建的小红书内容批量采集与 AI 聚合工具。

## 功能概览

- 从飞书多维表格读取待处理的小红书链接
- 自动抓取每条笔记的标题、作者、发布时间、收藏量、正文、图片、视频
- 调用配置的 AI 大模型解析图片内容和视频内容
- 生成综合性笔记内容总结
- 将所有结果实时回写飞书多维表格
- 网页端展示实时进度与日志，并保存历史运行记录

---

## 部署架构

本项目采用前后端分离部署：

| 组件 | 部署平台 | 说明 |
|------|----------|------|
| 前端 | GitHub Pages | 纯静态页面，免费托管 |
| 后端 | Render | Python FastAPI，支持 Playwright |

**在线访问地址**：`https://lxgtn.github.io/xhslink_260224/frontend/`

---

## 快速开始（在线版）

### 1. Fork 本仓库

点击右上角 Fork 按钮，将仓库复制到你的 GitHub 账号下。

### 2. 部署后端到 Render

1. 访问 [render.com](https://render.com) 使用 GitHub 账号登录
2. 点击 **"New"** → **"Web Service"**
3. 选择你 Fork 的 `xhslink_260224` 仓库
4. 配置如下：
   - **Name**: `xhslink_260224_backend`（或任意名称）
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && playwright install chromium`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. 选择 **Free** 套餐，点击 **Create Web Service**
6. 等待部署完成（约 3-5 分钟），复制分配的域名如 `https://xhslink-260224-backend.onrender.com`

### 3. 配置前端 API 地址

1. 在你的 Fork 仓库中，编辑 `frontend/js/app.js`
2. 修改第 9 行的 `API_BASE_URL`：
   ```javascript
   const API_BASE_URL = 'https://xhslink-260224-backend.onrender.com';
   ```
3. 提交更改

### 4. 启用 GitHub Pages

1. 打开你的 Fork 仓库 → **Settings** → **Pages**
2. Source 选择 **Deploy from a branch**
3. Branch 选择 **master** 或 **main**，文件夹选择 **/(root)**
4. 点击 **Save**

### 5. 配置飞书应用

1. 前往 [飞书开放平台](https://open.feishu.cn/app/)
2. 创建「企业自建应用」
3. 在「权限管理」中添加以下权限：
   - `drive:drive:readonly`（读取云空间文件）
   - `sheets:spreadsheet:readonly`（读取电子表格）
   - `sheets:spreadsheet:write`（编辑电子表格）
4. 发布应用（或在「测试企业和人员」中添加测试用户）
5. 在「凭证与基础信息」中获取 **App ID** 和 **App Secret**

### 6. 准备飞书多维表格

在你的飞书多维表格第一行添加如下表头（**列顺序可以任意调整**，只要表头名称匹配即可）：

| link | title | author | date | stars | text_original | pic_url_list | video_url_list | pic_processed | video_processed | summary | auto | error |
|------|-------|--------|-----|-------|---------------|--------------|----------------|---------------|-----------------|---------|------|-------|

然后从第 2 行起在 `link` 列填写小红书链接。

> **提示**：你可以根据自己的习惯调整列的顺序，只需确保第一行的表头名称与上表完全一致（不区分大小写）。

### 7. 开始使用

1. 访问你的 GitHub Pages 地址（如 `https://yourname.github.io/xhslink_260224/frontend/`）
2. 进入 **设置** 页面：
   - 配置 AI 模型（推荐 `gpt-4o`、`gemini-2.0-flash` 等视觉模型）
   - 配置飞书 App ID、App Secret 和表格 ID
   - 点击「测试连接」验证
3. 在设置页面获取小红书 Cookie
4. 返回控制台，点击「▶ 开始运行」

---

## 本地开发

如需本地运行或二次开发：

```bash
# 1. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 2. 启动开发服务器（本地模式，前端通过 FastAPI 静态文件服务提供）
python run.py
```

开发模式下访问 `http://localhost:8000`，前端会直接调用本地后端。

---

## 使用流程

### 第一次使用

1. **设置 → AI 模型配置**：填写模型厂商、模型名称和 API Key
   - 推荐使用支持视觉能力的模型，如 `gpt-4o`、`claude-3-5-sonnet-20241022`、`gemini-2.0-flash`
   - 视频解析建议使用 **Gemini** 系列（原生支持视频分析）

2. **设置 → 飞书多维表格**：
   - 填写「多维表格 ID」（URL 中间的字母数字串）
   - 填写飞书应用的「App ID」和「App Secret」
   - 点击「保存飞书配置」，然后点击「测试连接」验证

3. **设置 → 小红书 Cookie**：点击「获取 Cookie」，在弹出的浏览器中登录小红书，系统自动检测并保存登录状态

### 日常使用

1. 在飞书多维表格的 `link` 列填写待处理的小红书链接（`auto` 和 `error` 列留空）
2. 打开网页，点击「▶ 开始运行」
3. 控制台实时展示进度和日志
4. 处理完成后，飞书多维表格中对应行自动填入所有字段，`auto` 列设为 `1`

---

## 多维表格 ID 获取方式

打开你的飞书多维表格，复制 URL 中间的部分：

```
https://bytedance.feishu.cn/base/【这里就是多维表格 ID】
```

---

## 常见问题

**Q: 首次访问很慢？**
A: Render 免费套餐在无活动 15 分钟后会自动休眠，首次请求需要约 30 秒唤醒。

**Q: Cookie 获取后提示「Cookie 无效」？**
A: 请重新点击「获取 Cookie」，在弹出的浏览器中重新登录小红书。

**Q: 图片/视频解析失败？**
A: 检查 API Key 是否有效，以及所用模型是否支持多模态能力。视频解析推荐使用 Gemini。

**Q: 飞书连接测试失败？**
A: 请检查：
- App ID 和 App Secret 是否填写正确
- 飞书应用是否已发布，或你已被添加为测试用户
- 飞书应用是否已启用所需权限（多维表格读写权限）

**Q: 小红书内容抓取失败？**
A: Cookie 可能已过期，请在设置页面重新获取 Cookie。

**Q: 浏览器显示 CORS 错误？**
A: 检查 `app.js` 中的 `API_BASE_URL` 是否与 Render 分配的域名一致，并确保 Render 服务已成功部署。

---

## 项目结构

```
xhslink_260224/
├── run.py              # 本地启动入口
├── config.py           # 全局配置
├── requirements.txt
├── render.yaml         # Render 部署配置
├── DEPLOY.md           # 详细部署指南
├── app/
│   ├── main.py         # FastAPI 应用
│   ├── api/            # HTTP 路由
│   ├── services/       # 业务逻辑（爬虫/AI/Sheets/SSE）
│   ├── db/             # SQLite 数据层
│   └── schemas/        # Pydantic 数据模型
├── frontend/           # 前端静态文件（部署到 GitHub Pages）
│   ├── index.html
│   ├── css/
│   └── js/
└── data/               # 运行时数据（.gitignore 忽略）
    ├── xhs_cookies.json  # 自动生成
    └── xhslink.db        # SQLite 数据库（自动创建）
```

---

## 技术栈

- **后端**: Python 3.11 + FastAPI + Uvicorn
- **爬虫**: Playwright (Chromium)
- **AI**: OpenAI SDK (兼容所有 OpenAI API 格式的模型)
- **存储**: SQLite (aiosqlite)
- **实时通信**: Server-Sent Events (SSE)
- **前端**: 原生 HTML + CSS + JavaScript
- **部署**: GitHub Pages (前端) + Render (后端)
