# Gal Love Demo — API 契约说明

本文档描述 `gal-love-demo`（Vue 3 + TypeScript + Vite 前端）与 `gal-love-core`（FastAPI + SQLite 后端）之间**当前真实生效**的接口契约。

前端所有响应类型定义在 [`src/types/api.ts`](src/types/api.ts)，请求封装在 [`src/api/index.ts`](src/api/index.ts)。一切以这两处代码为准；本文不再描述旧版的 `/auth/*`、`/games/*`、`JWT`、`code/message/data` 包装和 `3000` 端口。

---

## 目录

- [基础约定](#基础约定)
- [本地启动](#本地启动)
- [认证与错误格式](#认证与错误格式)
- [端点总览](#端点总览)
- [端点详情](#端点详情)
- [前端类型对照](#前端类型对照)

---

## 基础约定

- 这是一个**个人向、单用户**的本地推荐系统，没有多用户、没有注册登录、没有鉴权。所有接口（包括 `/api/admin/*`）都可以直接调用。
- 后端 FastAPI 前缀统一为 `/api`。
- 前端 axios 实例 `baseURL` 固定为 `/api`（见 `src/api/index.ts`），超时 30 秒，请求头 `Content-Type: application/json`。
- **没有** `VITE_API_BASE_URL` 之类的环境变量；后端地址由 Vite 开发代理决定（见下）。
- 响应体是**裸 JSON 对象**，不是 `{ code, message, data }` 包装。列表通常是 `{ "items": [...], "total": ... }`。
- 时间字段为 ISO 8601 字符串；布尔值在 SQLite 中以 0/1 存储，经后端序列化后为 JSON `boolean`。

---

## 本地启动

```bash
# 1) 启动后端 gal-love-core（监听 8000）
cd gal-love-core
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
# Windows 可用： .venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000

# 2) 启动前端 gal-love-demo
cd gal-love-demo
npm install
npm run dev
```

- 前端开发服务器端口以 `vite.config.ts` 为准：当前配置 `5174`；被占用时 Vite 会顺延。后端 CORS 白名单同时允许 `5173` 与 `5174`（`http://localhost` 与 `http://127.0.0.1`），因此 `npm run dev` 落在 5173/5174 都能正常联调。
- `vite.config.ts` 中 `server.proxy` 将 **`/api`** 代理到 `http://127.0.0.1:8000`（`changeOrigin: true`）。因此浏览器里请求 `/api/works` 实际由 Vite 转发到后端 `http://127.0.0.1:8000/api/works`，无需在前端写死后端地址。
- 生产构建：`npm run build`（会先跑 `vue-tsc -b` 类型检查），预览：`npm run preview`。

---

## 认证与错误格式

**认证**：无。单用户本地工具，不带 `Authorization`、Cookie 或 token。

**错误**：FastAPI `HTTPException` / 请求校验失败时返回非 2xx，错误体统一为 `detail` 字段：

```json
{ "detail": "work not found" }
```

请求校验失败（Pydantic）时 `detail` 是数组：

```json
{
  "detail": [
    { "type": "int_parsing", "loc": ["query", "limit"], "msg": "Input should be a valid integer", "input": "abc" }
  ]
}
```

前端响应拦截器（`src/api/index.ts`）会把 `detail` 字符串直接作为错误消息；数组则拼接每条 `msg` 用「；」分隔；超时/网络错误也有对应中文提示。所有失败最终以 `Promise.reject(new Error(message))` 抛出，调用方用 `try/catch` 捕获即可。

---

## 端点总览

共 24 个端点，前端方法一一对应：

| 方法 | 路径 | 前端 `api` 方法 |
| --- | --- | --- |
| GET | `/api/health` | `health()` |
| GET | `/api/stats` | `stats()` |
| GET | `/api/works` | `works(params)` |
| GET | `/api/works/{id}` | `work(id)` |
| GET | `/api/works/{id}/similar` | `similar(id, limit)` |
| GET | `/api/tags` | `tags(params)` |
| GET | `/api/recommendations` | `recommendations(params)` |
| GET | `/api/me/entries` | `entries()` |
| PUT | `/api/me/entries/{id}` | `saveEntry(id, data)` |
| DELETE | `/api/me/entries/{id}` | `deleteEntry(id)` |
| POST | `/api/feedback` | `feedback(data)` |
| GET | `/api/settings` | `settings()` |
| PUT | `/api/settings` | `saveSettings(data)` |
| POST | `/api/admin/works` | `createWork(data)` |
| POST | `/api/admin/import/vndb` | `importVndb(data)` |
| POST | `/api/admin/import/bangumi` | `importBangumi(data)` |
| GET | `/api/admin/sync-runs` | `syncRuns(limit)` |
| GET | `/api/admin/duplicates` | `duplicates(limit, minScore)` |
| POST | `/api/admin/works/merge` | `mergeWorks(sourceId, targetId)` |
| GET | `/api/admin/backups` | `backups()` |
| POST | `/api/admin/backup` | `createBackup()` |
| POST | `/api/admin/restore` | `restoreBackup(filename)` |
| GET | `/api/admin/votes/stats` | `votesStats()` |
| POST | `/api/admin/votes/import` | `importVotes(data)` |

---

## 端点详情

### 系统

#### GET `/api/health`
健康检查，返回库路径、统计和推荐算法版本。

响应：`HealthResponse`
```json
{
  "status": "ok",
  "db": "data/gallove.db",
  "stats": { "works": 0, "tags": 0, "companies": 0, "entries": 0, "feedback": 0, "recommendations": 0, "sync_runs": 0 },
  "algorithm": "content+cf-v1"
}
```

#### GET `/api/stats`
响应：`Stats`（即 `HealthResponse.stats` 的同型对象）。

---

### 作品库

#### GET `/api/works`
筛选/搜索作品列表。

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `q` | string | — | 标题/简介/别名搜索 |
| `tag` | string | — | 标签名 |
| `status` | `want\|playing\|finished\|dropped\|none` | — | 我的清单状态，`none` 表示未加入 |
| `min_rating` | number (0–10) | — | 最低评分 |
| `sort` | `rating\|votes\|release\|title\|random` | `rating` | 排序 |
| `page` | int ≥1 | 1 | 页码 |
| `limit` | int 1–100 | 20 | 每页条数 |
| `include_nsfw` | boolean | `false` | 是否包含 NSFW |
| `platform` | string | — | 平台筛选（本轮新增） |
| `language` | string | — | 语言筛选（本轮新增） |
| `min_year` | int | — | 最早发行年份（本轮新增） |
| `max_length_minutes` | int ≥1 | — | 最长时长（分钟，本轮新增） |

响应：`WorkListResponse` = `{ items: Work[], total: number, page: number, limit: number }`

#### GET `/api/works/{id}`
响应：`Work`；不存在时 `404`，`detail: "work not found"`。

#### GET `/api/works/{id}/similar?limit=8`
相似作品。响应：`{ items: Work[] }`（`limit` 为 1–50，默认 10）。

#### GET `/api/tags?q=&limit=100`
标签列表。响应：`TagListResponse` = `{ items: TagInfo[] }`，`TagInfo` 为 `{ id, name, category?, work_count }`。

#### GET `/api/recommendations`
个性化推荐。

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `limit` | int 1–50 | 20 | 推荐条数 |
| `include_nsfw` | boolean\|null | null | 是否包含 NSFW，缺省用设置 |
| `min_year` | int 1900–2100 | — | 最早发行年份 |
| `max_length_minutes` | int ≥1 | — | 最长时长（分钟） |
| `platform` | string | — | 平台 |
| `language` | string | — | 语言 |
| `diversity` | number 0–0.6 | — | 多样性 |
| `save` | boolean | `true` | 是否落库为推荐批次 |
| `algorithm` | `auto\|content\|hybrid` | `auto` | 推荐算法（本轮新增） |

响应：`RecommendationResponse` = `{ items: Work[], batch_id: string | null, algorithm_version: string }`。`save=false` 时 `batch_id` 为 `null`。每条 `Work` 可能带 `score`、`reason`、`shared_tags`、`algorithm_version` 等推荐解释字段。

---

### 我的清单与反馈

#### GET `/api/me/entries`
响应：`EntryListResponse` = `{ items: Work[] }`（含 `entry` 字段）。

#### PUT `/api/me/entries/{id}`
请求体：`EntryInput`（`status`、`rating`、`favorite`、`notes`、`started_at`、`finished_at` 均可选）。
响应：更新后的 `Work`。作品不存在 `404`；非法字段值 `400`，`detail` 为原因。

#### DELETE `/api/me/entries/{id}`
响应：`{ "ok": true }`。

#### POST `/api/feedback`
请求体：`FeedbackInput`
```json
{ "work_id": 1, "kind": "like", "note": null }
```
`kind` 取 `not_interested | like | dislike | seen`。响应：`{ "ok": true }`。

---

### 设置

#### GET `/api/settings`
响应：`Settings`
```json
{
  "include_nsfw": false,
  "min_year": 2000,
  "max_length_minutes": 480,
  "platform": "Windows",
  "language": "zh-CN",
  "diversity": 0.2
}
```

#### PUT `/api/settings`
请求体：`SettingsPatch`（`Settings` 的任意子集）。响应：更新后的 `Settings`。

---

### 管理：作品与导入

#### POST `/api/admin/works`
手动新增作品。请求体：`ManualWorkInput`（`title` 必填，其余可选：`title_zh`、`original_title`、`description`、`cover_url`、`release_date`、`length_minutes`、`length_label`、`platforms[]`、`languages[]`、`rating`、`nsfw`、`tags[]`、`companies[]`、`titles[]`）。
响应：新建的 `Work`。

#### POST `/api/admin/import/vndb`
从 VNDB dump 导入。请求体：
```json
{ "limit": 100, "min_votes": 0, "wait": false, "incremental": false }
```
- `incremental`（本轮新增，默认 `false`）：`true` 时增量更新，只补缺失/变化的数据。
- `wait=false`（默认）：后台执行，响应 `ImportScheduledResponse` = `{ "status": "scheduled", "run_id": 12 }`。
- `wait=true`：同步执行，直接返回导入统计对象；导入失败为 `502`，`detail` 为错误文本。

#### POST `/api/admin/import/bangumi`
从 Bangumi 导入。请求体：
```json
{ "limit": 100, "avg_only": true, "wait": false, "incremental": false }
```
`incremental` 语义同上；响应规则同上。

#### GET `/api/admin/sync-runs?limit=20`
同步任务历史。响应：`SyncRunListResponse` = `{ items: SyncRun[] }`，`SyncRun` 为 `{ id, source, status, started_at, finished_at?, stats, error? }`。

---

### 管理：重复检测与合并（本轮新增）

#### GET `/api/admin/duplicates?limit=50&min_score=0.75`
检测疑似重复的作品对。

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `limit` | int | 50 | 最多返回条数 |
| `min_score` | number | 0.75 | 最低相似度 |

响应：`{ items: DuplicateCandidate[] }`
```json
{
  "items": [
    {
      "work_id": 12,
      "other_id": 87,
      "score": 0.98,
      "reasons": ["规范化标题完全相同", "外部引用相同: vndb:v123"]
    }
  ]
}
```
`reasons` 为中文可读的判定依据（相同外部引用、标题/别名高度重叠、公司与年份一致等）。

#### POST `/api/admin/works/merge`
合并作品，保留 `target_id`，删除 `source_id`。

请求体：
```json
{ "source_id": 12, "target_id": 87 }
```

响应：`MergeResult`
```json
{
  "ok": true,
  "source_id": 12,
  "target_id": 87,
  "moved": { "external_refs": 2, "titles": 3, "work_tags": 5, "work_companies": 1, "feedback": 0, "recommendations": 0, "my_entries": 1 }
}
```
`moved` 的 key 为表名，value 为实际迁移条数。非法参数（同一 id、不存在的工作等）返回 `400`，`detail` 为原因。

---

### 管理：备份与恢复（本轮新增）

#### GET `/api/admin/backups`
列出 `data/backups` 目录下所有有效 SQLite 备份，按创建时间倒序。

响应：`{ items: BackupInfo[] }`
```json
{
  "items": [
    { "filename": "gallove_20260101T120000_ab12cd.db", "path": "data/backups/gallove_20260101T120000_ab12cd.db", "size_bytes": 245760, "created_at": "2026-01-01T12:00:00+00:00" }
  ]
}
```

#### POST `/api/admin/backup`
创建一次事务一致性备份（无需请求体）。响应：`BackupResult`（结构同 `BackupInfo` 单个对象）。

#### POST `/api/admin/restore`
从 `backups` 目录中的文件恢复数据库，恢复前会自动做一次安全备份。

请求体：`{ "filename": "gallove_20260101T120000_ab12cd.db" }`

响应：`RestoreResult`
```json
{
  "ok": true,
  "db_path": "data/gallove.db",
  "backup_path": "data/backups/gallove_20260101T120000_ab12cd.db",
  "filename": "gallove_20260101T120000_ab12cd.db",
  "size_bytes": 245760,
  "auto_backup": { "filename": "...", "path": "...", "size_bytes": 245760, "created_at": "..." }
}
```
文件名不在备份目录、文件无效等情形返回 `400`。

---

### 管理：VNDB 票数库（本轮新增）

票数库是独立于主库的 SQLite 数据库（`data/votes.db`），用于协同过滤推荐。

#### GET `/api/admin/votes/stats`
响应：`VotesStats`
```json
{
  "path": "data/votes.db",
  "available": false,
  "votes": 0,
  "users": 0,
  "items": 0,
  "mean_score": null,
  "min_vote_count": 0,
  "max_vote_count": 0
}
```
`available=false` 表示票数库尚不存在或不可用，其余字段为 0 / null。

#### POST `/api/admin/votes/import`
导入 VNDB `votes.txt` dump。

请求体：`VotesImportInput`
```json
{ "dump_path": "/path/to/votes.txt", "min_votes": 10, "limit": 100000 }
```
- `dump_path`（必填）：dump 文件路径。
- `min_votes`：每部作品的最少投票人数过滤阈值，默认 10。
- `limit`：最多导入的投票行数，省略表示不限制。

响应：`VotesImportResult`
```json
{
  "dump": "/path/to/votes.txt",
  "db": "data/votes.db",
  "lines": 1000,
  "parsed": 990,
  "skipped": 10,
  "comments": 0,
  "min_votes": 10,
  "limit": 100000,
  "candidates": 50,
  "items_imported": 50,
  "votes_imported": 900,
  "imported": 900,
  "users": 300
}
```
dump 文件不存在时返回错误（前端拦截器会展示 `detail`）。

---

## 前端类型对照

所有响应/请求类型均导出自 `src/types/api.ts`，新增类型：

| 类型 | 对应端点 |
| --- | --- |
| `DuplicateCandidate` | `GET /api/admin/duplicates` |
| `MergeResult` | `POST /api/admin/works/merge` |
| `BackupInfo` / `BackupResult` | `GET /api/admin/backups`、`POST /api/admin/backup` |
| `RestoreResult` | `POST /api/admin/restore` |
| `VotesStats` | `GET /api/admin/votes/stats` |
| `VotesImportInput` / `VotesImportResult` | `POST /api/admin/votes/import` |
| `RecommendationAlgorithm`（`auto\|content\|hybrid`） | `GET /api/recommendations` 的 `algorithm` 参数 |

字段扩展：`WorkQuery` 新增 `platform`、`language`、`min_year`、`max_length_minutes`；`ImportVndbInput` / `ImportBangumiInput` 新增 `incremental`。既有类型名保持不变。

接口变更时，请同步更新本文、`src/types/api.ts` 与 `src/api/index.ts`。
