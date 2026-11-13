# FitWell Journal — 前端

移动优先的健身健康日志 Web/PWA。无构建工具：React 18 UMD + htm 模板语法，直接由 FastAPI 挂载在 `/` 下提供服务。

## 目录结构

```
frontend/
├── index.html              # 应用外壳（本地 vendor 引用）
├── manifest.webmanifest    # PWA 清单
├── sw.js                   # Service Worker（应用外壳 cache-first）
├── css/styles.css          # 主题样式（深青绿主题，CSS 变量）
├── js/api.js               # 后端 API 封装（/api/... 相对路径）
├── js/charts.js            # 手写 SVG 折线图（无第三方图表库）
├── js/app.js               # 主组件 + 底部 tab 路由
├── icons/                  # PWA 图标（192/512）
├── vendor/                 # react / react-dom / htm（UMD，已本地化）
└── tools/gen_icons.py      # 图标生成脚本（bundled Python + Pillow）
```

## vendor 说明

**vendor 为本地文件**，已从 unpkg 下载至 `vendor/`：

- react@18.3.1 → `vendor/react.production.min.js`
- react-dom@18.3.1 → `vendor/react-dom.production.min.js`
- htm@3.1.1 → `vendor/htm.umd.js`

如需重新下载，用简单单条命令（本环境复杂 try/catch 的 Invoke-WebRequest 可能报"非交互模式"错误）：

```powershell
Invoke-WebRequest -Uri "https://unpkg.com/react@18.3.1/umd/react.production.min.js" -OutFile "frontend\vendor\react.production.min.js"
```

若下载失败（网络不通），把 `index.html` 中三个本地 `<script src="vendor/...">` 替换为对应 CDN 标签即可：

```html
<script src="https://unpkg.com/react@18.3.1/umd/react.production.min.js"></script>
<script src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js"></script>
<script src="https://unpkg.com/htm@3.1.1/dist/htm.umd.js"></script>
```

## 图标重新生成

```powershell
& "C:\Users\pc\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" frontend\tools\gen_icons.py
```

## 运行

由后端 FastAPI 挂载 `frontend/` 目录后访问 `http://127.0.0.1:8000/`。API 走相对路径 `/api/...`，无需配置。

## 注意

- 周报页固定展示免责声明："本工具输出为趋势洞察，不构成医疗诊断或医疗建议。"
- Service Worker 不缓存 `/api/` 请求；升级前端静态资源时请更新 `sw.js` 中的 `CACHE_VERSION`。
