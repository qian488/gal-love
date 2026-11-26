# 代号G · 前端

个人向视觉小说 / AVG 推荐系统「代号G」的 **Web 前端**。配合 [`gal-love-core`](../gal-love-core)（FastAPI + SQLite）使用：后端负责抓取、清洗、推荐与数据治理，本仓库负责浏览、筛选、推荐展示、我的清单与反馈等交互。

**单用户本地工具**：没有注册、登录、鉴权或多用户概念，打开即可使用。数据全部存在本地 SQLite 数据库中。

## 能做什么

- **浏览作品库**：按标题/简介搜索，按标签、平台、语言、年份、时长、评分筛选，支持排序与分页。
- **查看详情**：作品元数据、多语言标题、标签、制作公司、外链引用，以及"相似作品"。
- **个性化推荐**：基于内容相似度与协同过滤（票数库）生成推荐，可切换 `auto / content / hybrid` 算法，展示推荐理由与共有标签。
- **我的清单**：把作品标记为"想玩 / 在玩 / 玩过 / 弃坑"，记录评分、收藏与笔记。
- **反馈**：对推荐结果给出"不感兴趣 / 喜欢 / 不喜欢 / 看过"，用于后续推荐优化。
- **偏好设置**：NSFW 开关、年份与时长区间、平台、语言、多样性。
- **管理功能**（`/api/admin/*`）：手动录入作品、从 VNDB / Bangumi 导入（支持增量）、重复作品检测与合并、数据库备份/恢复、VNDB 票数导入与统计、同步任务历史。

推荐算法的权重与评估方式见项目根目录 [`PLAN.md`](../PLAN.md) 第 5 节，界面只展示结果和推荐理由。

## 技术栈

- Vue 3（Composition API，`<script setup>`）+ TypeScript
- Vite 6（开发代理 `/api` → `127.0.0.1:8000`）
- Pinia（状态管理）、Vue Router 4
- Element Plus（UI）、Axios（HTTP）

## 快速开始

前置条件：Node.js（建议最新 LTS）与 Python 3.11+（`gal-love-core` 使用）。

```bash
# 1) 启动后端（在 gal-love-core 目录，监听 8000）
cd ../gal-love-core
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
# Windows: .venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000

# 2) 另开终端，启动前端
cd ../gal-love-demo
npm install
npm run dev
```

浏览器打开 `http://127.0.0.1:5174`（`vite.config.ts` 中固定为该端口；后端 CORS 同时放行 5173/5174）。

其他命令：

```bash
npm run build     # vue-tsc 类型检查 + 生产构建，输出到 dist/
npm run preview   # 预览生产构建
```

首次使用若库为空，可在「设置 / 管理」中执行 VNDB 或 Bangumi 导入，或手动录入作品。详细的接口参数与响应结构见 [`API_INTEGRATION.md`](API_INTEGRATION.md)。

> 前端不通过环境变量配置后端地址：`src/api/index.ts` 中 axios 的 `baseURL` 固定为 `/api`，由 `vite.config.ts` 的 `server.proxy` 转发到 8000 端口。`.env.development` 仅保留说明性注释。

导入数据源时有两点需要知道（界面里不展开）：

- VNDB 接口限流约 200 请求 / 5 分钟，大批量导入请用增量模式或官方 dump。
- Bangumi 建议在启动后端时设置 `GAL_LOVE_BANGUMI_UA`（带开发者 ID 与应用名），否则可能被限流。

## 目录说明

仓库根目录（`/gal-love`）：

| 目录 / 文件 | 说明 |
| --- | --- |
| `gal-love-core/` | **当前实际后端**：FastAPI 应用、SQLite 仓储、推荐引擎、导入脚本与测试。前端只对接这里的 `/api`。 |
| `gal-love-demo/` | **本前端项目**。 |
| `gal-love-backend/` | 早期留下的 Java 后端骨架与对接指南，当前前端**未对接**，其文档中的注册登录 / JWT / `code,message,data` 约定均已废弃。 |
| `PLAN.md` | 产品计划、技术决策与实施进度。 |
| `readme.md` | 「代号G」项目总览与快速开始。 |
| `index.html` | 早期占位文件，无实际用途。 |

`gal-love-demo/` 内部：

```
gal-love-demo/
├── public/                 静态资源
├── src/
│   ├── api/index.ts        axios 实例、错误拦截器、全部 API 调用方法
│   ├── types/api.ts        请求/响应 TypeScript 类型定义
│   ├── components/         可复用组件（WorkCard、CoverImage、EntryDialog、备份/合并/投票面板等）
│   ├── layouts/            主布局 MainLayout
│   ├── router/             路由配置
│   ├── store/              Pinia 状态（game）
│   ├── views/              页面：Home、Explore、Library、WorkDetail、Settings、Onboarding、PersonaHub、PersonaQuiz、PairwiseTest、TarotDraw、404
│   ├── style.css           全局样式
│   ├── App.vue / main.ts   应用入口
│   └── types/              其他声明文件（路由元信息、Vue shims 等）
├── vite.config.ts          Vite 配置（端口、/api 代理）
├── tsconfig*.json          TypeScript 配置
├── .env.development        开发说明（无生效变量）
├── API_INTEGRATION.md      前后端接口契约
└── README.md               本文件
```

## 数据说明

- 主库：`gal-love-core/data/gallove.db`（作品、标签、公司、我的清单、反馈、推荐批次、同步记录）。
- 票数库：`gal-love-core/data/votes.db`（独立的 VNDB 投票数据，用于协同过滤）。
- 备份：`gal-love-core/data/backups/*.db`，可通过管理接口创建与恢复。

所有数据都在本机，删除数据库文件即重置。
