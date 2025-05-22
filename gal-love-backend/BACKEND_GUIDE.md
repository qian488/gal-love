# Gal Love Demo - 后端开发对接指导

本指南用于后端开发者实现与本前端系统（Vue 3 + TypeScript + Vite + Pinia + Element Plus）对接的接口，确保功能完整、联调顺畅。

---

## 目录
- [接口基础规范](#接口基础规范)
- [用户模块接口](#用户模块接口)
- [游戏模块接口](#游戏模块接口)
- [通用返回结构](#通用返回结构)
- [接口安全与认证](#接口安全与认证)
- [联调建议](#联调建议)

---

## 接口基础规范
- 所有接口建议以 RESTful 风格设计，返回 JSON。
- 所有接口返回结构需包含 `code`（0为成功，非0为错误）、`message`（提示信息）、`data`（具体数据）。
- 登录后需返回 JWT token，前端会在后续请求 header 加 `Authorization: Bearer <token>`。
- 支持跨域（CORS）。

---

## 用户模块接口

### 1. 用户注册
- `POST /auth/register`
- 请求体：
  - username: string
  - email: string
  - password: string
- 返回：`{ code, message }`

### 2. 用户登录
- `POST /auth/login`
- 请求体：
  - username: string
  - password: string
- 返回：
  - code: 0
  - message: "success"
  - data: { token: string, user: { id, username, email, ... } }

### 3. 获取用户信息
- `GET /user/profile`
- header: `Authorization: Bearer <token>`
- 返回：`{ code, message, data: { id, username, email, ... } }`

### 4. 更新用户信息
- `PUT /user/profile`
- header: `Authorization: Bearer <token>`
- 请求体：部分字段
- 返回：同上

---

## 游戏模块接口

### 1. 获取游戏列表
- `GET /games`
- 支持 query 参数：page, limit, tags, search
- 返回：
  - code: 0
  - message: "success"
  - data: { games: [...], total, page, limit }

### 2. 获取游戏详情
- `GET /games/:id`
- 返回：`{ code, message, data: { ... } }`

### 3. 获取推荐游戏
- `GET /games/recommendations`
- header: `Authorization: Bearer <token>`（如需个性化推荐）
- 返回：`{ code, message, data: [...] }`

### 4. 游戏评分
- `POST /games/:id/rate`
- header: `Authorization: Bearer <token>`
- 请求体：{ rating: number }
- 返回：`{ code, message }`

### 5. 游戏评论
- `POST /games/:id/comments`
- header: `Authorization: Bearer <token>`
- 请求体：{ content: string }
- 返回：`{ code, message }`

---

## 通用返回结构
```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```
- code=0 表示成功，非0为错误（如 401 未登录，403 权限不足，400 参数错误等）。
- message 用于前端弹窗提示。
- data 为具体业务数据。

---

## 接口安全与认证
- 推荐使用 JWT 进行用户认证。
- 注册、登录接口无需认证，其余接口需校验 token。
- token 失效时返回 401，前端会自动跳转登录页。
- 建议接口限流、防刷。

---

## 联调建议
- 前端接口类型定义详见 `src/types/api.ts`，可参考字段设计。
- 返回字段如有调整，请及时与前端沟通并同步更新。
- 推荐本地开发时前后端端口分别为 3000（后端）和 5173（前端），支持 CORS。
- 推荐接口返回 mock 数据，便于前端开发。

---

如有疑问请随时与前端开发沟通，保持接口一致性和联调效率。


后端需要实现以下核心功能，以支持前端 Gal Love Demo 推荐系统的完整体验：

### 1. 用户模块
- **用户注册**：接收用户名、邮箱、密码，完成新用户注册，校验唯一性，返回注册结果。
- **用户登录**：校验用户名和密码，返回 JWT token 及用户信息。
- **获取用户信息**：根据 token 返回当前登录用户的详细信息。
- **更新用户信息**：支持用户修改个人资料（如昵称、邮箱、头像等），需校验 token。

### 2. 游戏模块
- **获取游戏列表**：支持分页、标签筛选、关键词搜索，返回游戏数组及总数。
- **获取游戏详情**：根据游戏 ID 返回详细信息。
- **获取推荐游戏**：可根据用户兴趣、历史行为等返回个性化推荐（如无推荐算法可先返回热门/随机）。
- **游戏评分**：用户可对游戏进行评分，需校验 token，支持单用户单游戏唯一评分。
- **游戏评论**：用户可对游戏发表评论，需校验 token，支持评论内容存储与展示。

### 3. 通用
- **统一的接口返回结构**：所有接口返回 `{ code, message, data }`，code=0 表示成功，非0为错误。
- **认证与安全**：除注册、登录外，所有接口需校验 JWT token，token 失效返回 401。
- **CORS 支持**：允许前端本地开发端口跨域访问。
- **Mock 数据支持**（开发阶段可选）：便于前端调试。

### 4. 推荐（可选/进阶）
- **个性化推荐算法**：根据用户行为、偏好、评分等生成推荐列表。
- **标签/分类管理**：支持游戏多标签、分类筛选。

---

后端只需严格按照接口文档（API_INTEGRATION.md、BACKEND_GUIDE.md）实现上述功能，即可与前端无缝对接。

# 核心技术栈推荐
1. 主框架与语言
Spring Boot + Java/Kotlin
成熟稳定的企业级框架
完善的生态系统
适合快速开发 RESTful API
内置强大的安全机制
2. 数据库
主数据库: MySQL/PostgreSQL
存储用户、游戏、评论等基础数据
支持复杂查询和事务
缓存: Redis
缓存热门游戏数据
存储用户会话信息
实现接口限流
3. 安全认证
Spring Security + JWT
实现用户认证授权
支持文档要求的 token 机制
方便的权限控制
4. API 文档
Swagger/OpenAPI
自动生成 API 文档
方便前端对接
支持接口测试
推荐系统部分
1. 基础推荐实现
协同过滤算法
可使用 Apache Mahout 或 LightFM
基于用户评分和行为数据
适合冷启动阶段
2. 进阶推荐方案
ElasticSearch
实现游戏全文搜索
支持标签筛选
分析用户行为