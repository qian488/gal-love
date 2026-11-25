# 代号G

个人向视觉小说 / AVG 推荐系统。它从 VNDB、Bangumi 和手工录入聚合作品，记录你玩过什么、喜欢什么，然后回答一个问题：**下一部玩什么？**

单用户、本地运行、无注册登录。数据全部存在本机的 SQLite 里。

## 目录

| 目录 / 文件 | 说明 |
| --- | --- |
| `gal-love-core/` | 主运行链路：FastAPI + SQLite，负责数据导入、标签与搜索、推荐算法、备份恢复和测试。 |
| `gal-love-demo/` | Vue 3 + Vite 前端，只对接 core 的 `/api`。使用说明见 [`gal-love-demo/README.md`](gal-love-demo/README.md)。 |
| `gal-love-backend/` | 早期 Java 后端骨架，仅保留参考，不再运行；其中的注册登录 / JWT 约定已废弃。 |
| `PLAN.md` | 产品计划、技术决策、实施进度与已知取舍，是项目状态的事实来源。 |
| `index.html` | 早期占位文件，无实际用途。 |

## 快速开始

```bash
# 后端：监听 127.0.0.1:8000
cd gal-love-core
python -m venv .venv
.venv\Scripts\activate          # Windows；macOS/Linux 用 source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 前端：另开终端，监听 5174，/api 代理到后端
cd gal-love-demo
npm install
npm run dev
```

打开终端给出的地址（通常 `http://127.0.0.1:5174`）。Vite 的 `/api` 代理把请求转发到 8000，前端不需要额外配置后端地址。

首次使用库为空时，可在「设置」里导入 VNDB / Bangumi 数据或手工录入作品；也可以在首页走三步引导，挑几部喜欢的作品后直接得到推荐。

## 常用命令

```bash
# 后端测试（Windows 用项目自带虚拟环境）
cd gal-love-core && .venv/Scripts/python.exe -m pytest -q

# 前端类型检查 + 生产构建
cd gal-love-demo && npm run build

# 增量同步（首次导入后可用）
cd gal-love-core && .venv/Scripts/python.exe -m app.scheduler --once
```

## 数据

- 主库：`gal-love-core/data/gallove.db`（作品、标签、我的清单、反馈、推荐快照、同步记录）。
- 票数库：`gal-love-core/data/votes.db`（独立的 VNDB 投票数据，用于混合推荐）。
- 备份：`gal-love-core/data/backups/`，通过管理接口创建与恢复；恢复前会自动留一份当前数据。
- 这些文件都不进版本库，删除即重置。

接口的完整请求/响应契约见 [`gal-love-demo/API_INTEGRATION.md`](gal-love-demo/API_INTEGRATION.md)。
