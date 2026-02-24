# XHS Link – 小红书内容聚合工具

基于 Python + FastAPI + Playwright 构建的小红书内容批量采集与 AI 聚合工具。

## 功能概览

- 从 Google Sheets 读取待处理的小红书链接
- 自动抓取每条笔记的标题、作者、发布时间、收藏量、正文、图片、视频
- 调用配置的 AI 大模型解析图片内容和视频内容
- 生成综合性笔记内容总结
- 将所有结果实时回写 Google Sheets
- 网页端展示实时进度与日志，并保存历史运行记录

---

## 安装步骤

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 Playwright 浏览器

```bash
playwright install chromium
```

### 3. 配置 Google Sheets OAuth2

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目 → 启用 **Google Sheets API**
3. 创建 **OAuth 2.0 客户端 ID**（应用类型选「桌面应用」）
4. 下载 JSON 凭据文件，**重命名为 `credentials.json`**
5. 将 `credentials.json` 放入本项目的 `data/` 目录（若目录不存在请手动创建）

### 4. 准备 Google Sheets

在你的 Google Sheets 第一行添加如下表头（列顺序必须严格一致）：

| A | B | C | D | E | F | G | H | I | J | K | L | M |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| link | title | author | date | stars | text_original | pic_url_list | video_url_list | pic_processed | video_processed | summary | auto | error |

然后从第 2 行起在 A 列填写小红书链接。

---

## 启动应用

```bash
python run.py
```

启动后浏览器会自动打开 `http://localhost:8000`。

---

## 使用流程

### 第一次使用

1. **设置 → AI 模型配置**：填写模型厂商、模型名称和 API Key，点击「保存 AI 配置」
   - 推荐使用支持视觉能力的模型，如 `gpt-4o`、`claude-3-5-sonnet-20241022`、`gemini-2.0-flash`
   - 视频解析建议使用 **Gemini** 系列（原生支持视频分析）

2. **设置 → Google Sheets**：填写 Sheets ID（URL 中间的字母数字串），点击「授权 Google 账号」完成 OAuth 授权

3. **设置 → 小红书 Cookie**：点击「获取 Cookie」，在弹出的浏览器中登录小红书，系统自动检测并保存登录状态

### 日常使用

1. 在 Google Sheets 中的 A 列填写待处理的小红书链接（auto 和 error 列留空）
2. 打开 `http://localhost:8000`，点击「▶ 开始运行」
3. 控制台实时展示进度和日志
4. 处理完成后，Google Sheets 中对应行自动填入所有字段，`auto` 列设为 `1`

---

## Sheets ID 获取方式

打开你的 Google Sheets，复制 URL 中间的部分：

```
https://docs.google.com/spreadsheets/d/【这里就是 Sheets ID】/edit
```

---

## 常见问题

**Q: Cookie 获取后提示「Cookie 无效」？**
A: 请重新点击「获取 Cookie」，在弹出的浏览器中重新登录小红书。

**Q: 图片/视频解析失败？**
A: 检查 API Key 是否有效，以及所用模型是否支持多模态能力。视频解析推荐使用 Gemini。

**Q: Google 授权按钮灰色？**
A: 请先将 `credentials.json` 放入 `data/` 目录。

**Q: 小红书内容抓取失败？**
A: Cookie 可能已过期，请在设置页面重新获取 Cookie。

---

## 项目结构

```
xhslink_260224/
├── run.py              # 启动入口
├── config.py           # 全局配置
├── requirements.txt
├── app/
│   ├── main.py         # FastAPI 应用
│   ├── api/            # HTTP 路由
│   ├── services/       # 业务逻辑（爬虫/AI/Sheets/SSE）
│   ├── db/             # SQLite 数据层
│   └── schemas/        # Pydantic 数据模型
├── frontend/           # 前端静态文件
└── data/               # 运行时数据（.gitignore 忽略）
    ├── credentials.json  # 需手动放入
    ├── token.json        # 自动生成
    ├── xhs_cookies.json  # 自动生成
    └── xhslink.db        # SQLite 数据库（自动创建）
```
