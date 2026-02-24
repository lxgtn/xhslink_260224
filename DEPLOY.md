# XHS Link 分离部署指南

本指南介绍如何将 XHS Link 部署到 **Render（后端）** + **GitHub Pages（前端）**，实现通过网页直接访问，无需本地运行。

---

## 架构说明

| 组件 | 部署位置 | 说明 |
|------|----------|------|
| 前端（HTML/JS） | GitHub Pages | 纯静态页面，免费托管 |
| 后端（Python FastAPI） | Render | 支持 Playwright、SQLite，有免费套餐 |

---

## 第一步：部署后端到 Render

### 1. 注册 Render 账号

访问 [render.com](https://render.com) 使用 GitHub 账号登录。

### 2. 创建 Web Service

1. 点击 **"New"** → **"Web Service"**
2. 选择你的 `xhslink_260224` GitHub 仓库
3. 配置如下：
   - **Name**: `xhslink_260224_backend`（或任意名称）
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && playwright install chromium
     ```
   - **Start Command**:
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
4. 选择 **Free** 套餐
5. 点击 **"Create Web Service"**

### 3. 等待部署完成

首次部署可能需要 3-5 分钟（需要下载 Chromium）。

### 4. 获取后端 URL

部署完成后，Render 会分配一个域名：

```
https://xhslink-260224-backend.onrender.com
```

复制这个 URL，下一步需要用到。

---

## 第二步：配置前端 API 地址

### 1. 修改前端配置

编辑 `frontend/js/app.js`：

```javascript
// 将这一行：
const API_BASE_URL = '';  // 本地运行

// 改为你的 Render URL：
const API_BASE_URL = 'https://xhslink-260224-backend.onrender.com';  // 生产环境
```

### 2. 提交更改

```bash
git add .
git commit -m "Configure API endpoint for Railway"
git push
```

---

## 第三步：部署前端到 GitHub Pages

### 1. 启用 GitHub Pages

1. 打开 GitHub 仓库 → **Settings** → **Pages**
2. Source 选择 **Deploy from a branch**
3. Branch 选择 **master** / **main**，文件夹选择 **/(root)**
4. 点击 **Save**

### 2. 配置静态文件

由于 GitHub Pages 从仓库根目录托管，需要确保前端文件路径正确。

在仓库根目录创建 `index.html` 指向 `frontend/index.html`：

```html
<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="refresh" content="0;url=frontend/index.html">
</head>
<body>
  <p>Redirecting to <a href="frontend/index.html">XHS Link</a>...</p>
</body>
</html>
```

或者直接将 `frontend/` 目录内容复制到根目录（使用 GitHub Actions 自动完成）。

### 3. 访问页面

几分钟后，你的应用将在以下地址可用：

```
https://lxgtn.github.io/xhslink_260224/frontend/
```

---

## 第四步：验证部署

1. 打开 GitHub Pages 链接
2. 进入 **设置** 页面
3. 填写飞书 App ID、App Secret 和表格 ID
4. 点击 **测试连接** 验证后端通信正常

---

## 故障排查

### 问题：前端无法连接后端

**症状**：测试连接时提示 "检查失败"

**解决方案**：
1. 检查 `app.js` 中的 `API_BASE_URL` 是否正确
2. 检查 Render 应用是否正在运行（可能处于休眠状态，首次请求需等待 30 秒唤醒）
3. 打开浏览器开发者工具 → Network 标签，查看具体错误

### 问题：CORS 错误

**症状**：浏览器控制台显示 CORS policy 错误

**解决方案**：
确保 `main.py` 中已启用 CORS：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://lxgtn.github.io"],  # 你的 GitHub Pages 域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 问题：Cookie 获取失败

**症状**：点击"获取 Cookie"无反应

**原因**：Playwright 浏览器只能在服务器端运行，无法通过浏览器直接操作

**解决方案**：这是设计限制，Cookie 获取仍需要在服务器端完成。建议：
- 在本地获取 Cookie 后，通过设置页面的表单手动输入 Cookie
- 或使用本地版本获取 Cookie，然后复制到 Render 环境

### 问题：Render 服务休眠

**症状**：首次请求很慢（30秒以上）

**原因**：Render 免费套餐在无活动 15 分钟后会自动休眠

**解决方案**：
- 这是正常现象，等待服务唤醒即可
- 如需持续运行，可升级到付费套餐（$7/月）

---

## 费用说明

| 服务 | 免费额度 | 说明 |
|------|----------|------|
| Render | 750小时/月 | 足够个人使用，15分钟无活动后休眠 |
| GitHub Pages | 无限 | 静态页面免费 |

---

## 其他部署选项

### Railway（付费）

如果需要持续运行不休眠：
1. 访问 [railway.app](https://railway.app)
2. 免费额度：$5/月或 500 小时
3. 已配置 `railway.json` 和 `Procfile`

### Hugging Face Spaces

支持 Docker 部署，也有免费额度。
