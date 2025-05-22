# Gal Love Demo - 前端与后端接口对接说明

本项目为 Galgame 推荐系统的前端部分，基于 Vue 3 + TypeScript + Vite + Pinia + Element Plus 实现。本文档用于说明前端与后端接口对接的相关约定和注意事项，便于后续联调。

## 目录
- [接口基础约定](#接口基础约定)
- [用户相关接口](#用户相关接口)
- [游戏相关接口](#游戏相关接口)
- [全局约定](#全局约定)
- [接口返回示例](#接口返回示例)

---

## 接口基础约定
- 所有接口基础地址由 `.env` 文件中的 `VITE_API_BASE_URL` 控制，开发环境默认 `http://localhost:3000`。
- 所有需要登录的接口需在 header 中携带 `Authorization: Bearer <token>`。
- 前端通过 axios 封装统一请求，错误处理已在响应拦截器中实现。

---

## 用户相关接口

### 1. 用户注册
- `POST /auth/register`
- 请求体：
```json
{
  "username": "string",
  "email": "string",
  "password": "string"
}
```
- 返回：`{ code, message }`

### 2. 用户登录
- `POST /auth/login`
- 请求体：
```json
{
  "username": "string",
  "password": "string"
}
```
- 返回：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "jwt-token",
    "user": { "id": 1, "username": "xxx", "email": "xx@xx.com", ... }
  }
}
```

### 3. 获取用户信息
- `GET /user/profile`
- header: `Authorization: Bearer <token>`
- 返回：
```json
{
  "code": 0,
  "message": "success",
  "data": { "id": 1, "username": "xxx", "email": "xx@xx.com", ... }
}
```

### 4. 更新用户信息
- `PUT /user/profile`
- header: `Authorization: Bearer <token>`
- 请求体：部分字段
- 返回：同上

---

## 游戏相关接口

### 1. 获取游戏列表
- `GET /games`
- 支持 query 参数：`page, limit, tags, search`
- 返回：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "games": [ { "id": 1, "title": "...", ... } ],
    "total": 100,
    "page": 1,
    "limit": 12
  }
}
```

### 2. 获取游戏详情
- `GET /games/:id`
- 返回：
```json
{
  "code": 0,
  "message": "success",
  "data": { "id": 1, "title": "...", ... }
}
```

### 3. 获取推荐游戏
- `GET /games/recommendations`
- header: `Authorization: Bearer <token>`（如需登录）
- 返回：
```json
{
  "code": 0,
  "message": "success",
  "data": [ { "id": 1, "title": "...", ... } ]
}
```

### 4. 游戏评分
- `POST /games/:id/rate`
- header: `Authorization: Bearer <token>`
- 请求体：`{ rating: number }`
- 返回：`{ code, message }`

### 5. 游戏评论
- `POST /games/:id/comments`
- header: `Authorization: Bearer <token>`
- 请求体：`{ content: string }`
- 返回：`{ code, message }`

---

## 全局约定
- 所有接口返回结构：
```json
{
  "code": 0, // 0 表示成功，非0为错误
  "message": "success or error message",
  "data": ... // 具体数据
}
```
- 登录失效时，前端会自动跳转到登录页。
- 业务错误会通过 message 弹窗提示。

---

## 接口返回示例
详见 `src/types/api.ts`，所有字段类型已在前端定义。

如需联调或有接口变更，请同步更新本文件和 `src/api/index.ts`。
