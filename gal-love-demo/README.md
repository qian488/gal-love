# Gal Love Demo - 视觉小说推荐系统UI

## 项目概述

这是一个基于Vue 3、TypeScript和Vite构建的视觉小说（Galgame）推荐系统的前端界面。该项目旨在为用户提供个性化的视觉小说推荐，并提供友好的用户界面来浏览和发现新的游戏。

## 项目结构

```
.
├── .gitignore           # Git忽略文件配置
├── .vscode/             # VSCode编辑器配置
├── README.md            # 项目文档
├── index.html           # 入口HTML文件
├── package.json         # 项目依赖和脚本配置
├── public/              # 静态资源目录
│   └── vite.svg         # Vite logo
├── src/                 # 源代码目录
│   ├── App.vue          # 应用主组件
│   ├── assets/          # 资源文件目录
│   │   └── vue.svg      # Vue logo
│   ├── components/      # 组件目录
│   │   └── HelloWorld.vue # 示例组件
│   ├── main.ts          # 应用入口文件
│   ├── style.css        # 全局样式
│   └── vite-env.d.ts    # Vite环境类型声明
├── tsconfig.json        # TypeScript配置
├── tsconfig.app.json    # 应用TypeScript配置
├── tsconfig.node.json   # Node环境TypeScript配置
└── vite.config.ts       # Vite配置文件
```

## 技术栈

- **前端框架**: Vue 3 (^3.5.13)
- **开发语言**: TypeScript (^5.7.2)
- **构建工具**: Vite (^6.3.1)
- **类型检查**: Vue-tsc (^2.2.8)
- **插件**: @vitejs/plugin-vue (^5.2.2)

## 功能特性

- 基于Vue 3的现代化组件架构
- 使用TypeScript提供类型安全
- 采用Vite实现快速的开发体验和构建性能
- 使用Vue 3的Composition API和`<script setup>`语法糖简化组件开发

## 开发指南

### 环境要求

- Node.js (推荐最新LTS版本)
- npm或yarn包管理器

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

当前项目处于初始开发阶段，基于Vue 3 + TypeScript + Vite模板创建。主要功能和UI组件尚待实现。

## 原始模板信息

This template should help get you started developing with Vue 3 and TypeScript in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about the recommended Project Setup and IDE Support in the [Vue Docs TypeScript Guide](https://vuejs.org/guide/typescript/overview.html#project-setup).
