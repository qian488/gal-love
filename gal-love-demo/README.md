# Gal Love Demo - 视觉小说推荐系统UI

## 项目概述

这是一个基于 Vue 3、TypeScript 和 Vite 构建的视觉小说（Galgame）推荐系统前端界面。项目旨在为用户提供个性化的 Galgame 推荐、浏览、筛选、注册登录等功能，界面现代美观，交互友好。

## 主要功能

- 用户注册、登录、登出、个人信息管理
- 游戏列表浏览、详情查看、标签筛选、搜索
- 首页推荐、热门、最新发布游戏展示
- 路由权限控制（未登录用户无法访问个人中心等页面）
- 全局布局与导航栏，404 页面
- 使用 Pinia 进行状态管理
- 使用 Element Plus 作为 UI 框架
- 支持 TypeScript 类型安全

## 技术栈

- Vue 3 (Composition API, `<script setup>`)
- TypeScript
- Vite
- Pinia
- Vue Router 4
- Element Plus
- Axios

## 项目结构

```
.
├── public/                # 静态资源
├── src/
│   ├── api/               # API 封装
│   ├── assets/            # 图片等资源
│   ├── components/        # 可复用组件
│   ├── hooks/             # 自定义 hooks
│   ├── layouts/           # 布局组件
│   ├── router/            # 路由配置
│   ├── store/             # Pinia 状态管理
│   ├── styles/            # 样式
│   ├── types/             # 类型定义
│   └── views/             # 页面视图
├── App.vue                # 应用主入口
├── main.ts                # 入口文件
├── vite.config.ts         # Vite 配置
├── tsconfig*.json         # TypeScript 配置
└── README.md              # 项目说明
```

## 开发指南

### 环境要求

- Node.js (推荐最新LTS版本)
- npm 或 yarn 包管理器

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 项目状态

- 已完成基础页面和路由结构
- 用户认证、注册、登出、路由守卫等功能已实现
- 首页、游戏列表、游戏详情、个人中心等页面已搭建
- 目前部分数据为 mock，后续可对接后端 API
- UI 基于 Element Plus，支持响应式布局
