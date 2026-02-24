# XHS Link 分离部署指南

本指南介绍如何将 XHS Link 部署到 **Railway（后端）** + **GitHub Pages（前端）**，实现通过网页直接访问，无需本地运行。

---

## 架构说明

| 组件 | 部署位置 | 说明 |
|------|----------|------|
| 前端（HTML/JS） | GitHub Pages | 纯静态页面，免费托管 |
| 后端（Python FastAPI） | Railway | 支持 Playwright、SQLite |

---

## 第一步：部署后端到 Railway

### 1. 注册 Railway 账号

访问 [railway.app](https://railway.app) 使用 GitHub 账号登录。

### 2. 创建新项目

1. 点击 **"New Project"**
2. 选择 **"Deploy from GitHub repo"**
3. 选择你的 `xhslink_260224` 仓库
4. Railway 会自动检测配置并部署

### 3. 配置环境变量

在项目设置中添加以下环境变量：

```
PYTHON_VERSION=3.11
```

### 4. 获取后端 URL

部署完成后，Railway 会分配一个域名：

```
https://your-app-name.up.railway.app
```

复制这个 URL，下一步需要用到。

### 5. 安装 Playwright

由于 Railway 使用容器部署，需要在部署后安装浏览器：

1. 进入 Railway 项目的 **"Shell"** 标签
2. 运行：`playwright install chromium`

---

## 第二步：配置前端 API 地址

### 1. 修改前端配置

编辑 `frontend/js/app.js`：

```javascript
// 将这一行：
const API_BASE_URL = '';  // 本地运行

// 改为你的 Railway URL：
const API_BASE_URL = 'https://your-app-name.up.railway.app';  // 生产环境
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
2. 检查 Railway 应用是否正在运行
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
- 在 Railway Shell 中手动运行 Cookie 获取脚本
- 或暂时使用本地版本获取 Cookie，然后上传到 Railway

---

## 费用说明

| 服务 | 免费额度 | 说明 |
|------|----------|------|
| Railway | $5/月 或 500小时 | 足够个人使用 |
| GitHub Pages | 无限 | 静态页面免费 |

---

## 备选方案

如果 Railway 不稳定，可以考虑：

### Render（免费）

1. 访问 [render.com](https://render.com)
2. 创建 Web Service，选择 Python
3. 构建命令：`pip install -r requirements.txt && playwright install chromium`
4. 启动命令：`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Hugging Face Spaces

支持 Docker 部署，也有免费额度。
