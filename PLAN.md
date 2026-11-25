# Gal Love 个人向推荐系统计划

> 版本：0.2  
> 更新时间：2026-11-25  
> 状态：Phase 0–4 全部落地。Phase 1 补齐增量同步/定时、重复合并、标签中文化；Phase 2 补齐冷启动引导；Phase 3 完成 votes 导入、Item-CF、混合排序与离线评估；Phase 4 完成前端页面、中文搜索、封面缓存、过滤 UI、合并 UI 与备份恢复。验证：后端 67 项测试通过，前端 `npm run build` 通过；前后端联调运行正常。

---

## 1. 产品定位

Gal Love 是一个**个人向视觉小说 / AVG 推荐系统**。

它从 VNDB、Bangumi 和手工录入中聚合作品资料，记录“我”的游戏经历与口味，用推荐算法持续回答一个问题：

> **下一部玩什么？**

核心闭环：

```text
聚合作品资料 → 建立我的游戏库/口味档案 → 算法推荐 → 我反馈 → 推荐变准
```

### 目标

- 单用户优先，先为自己服务
- 覆盖所有视觉小说 / AVG，不限于 Galgame
- 推荐算法是核心能力
- 数据可持续同步、可手工修正
- 本地即可运行，不依赖 MySQL/Redis/Java 环境

### 非目标（当前阶段）

- 多用户注册、登录、权限体系
- 评论、点赞、关注、动态等社区功能
- 游戏下载、购买、分发
- 商业化、广告、会员
- 复杂管理后台

---

## 2. 技术决策

### 2.1 新核心：Python + FastAPI + SQLite

现有 Spring Boot 后端保留为历史参考（`gal-love-backend/`），不再作为主运行链路。

原因：

- 单用户、算法优先，Python 更适合数据处理和推荐算法迭代
- SQLite 零配置，便于本地运行和备份
- 当前环境没有 Java/Maven/MySQL，旧后端无法验证
- FastAPI 自带 OpenAPI 文档，前后端联调成本低
- 后续需要多用户或云部署时，可平滑迁移到 PostgreSQL

### 2.2 目录规划

```text
gal-love/
├── PLAN.md                    # 本计划
├── gal-love-core/             # 新的个人推荐核心（Python）
│   ├── app/                   # FastAPI 应用与领域逻辑
│   ├── scripts/               # 数据导入、推荐调试脚本
│   ├── tests/                 # 算法与 API 测试
│   └── data/                  # 本地 SQLite 数据库（不提交）
├── gal-love-demo/             # 前端（后续按新 API 改造）
└── gal-love-backend/          # 旧 Spring Boot 后端（保留参考）
```

### 2.3 运行方式

```bash
cd gal-love-core
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

---

## 3. 数据模型

以 **Work（作品）** 为最小单位，不以 Release（发行版）为单位。

```text
works              作品主表
titles             多语言标题、别名
tags               统一标签
work_tags          作品-标签权重
companies          开发商/发行商
work_companies     作品-公司关系
external_refs      外部来源映射（vndb / bangumi / manual）
my_entries         我的状态、评分、收藏、备注
feedback           不感兴趣等显式反馈
recommendations    推荐结果快照（分数、理由、算法版本）
sync_runs          数据同步记录
settings           本地设置
```

关键约束：

- `external_refs(source, external_id)` 唯一
- 手工修正的数据不被后续同步覆盖
- 推荐结果保存算法版本，便于对比
- 原始 JSON 保存在 `external_refs.raw_json`，便于回溯

---

## 4. 内容范围与数据源

### 4.1 收录范围

建议收录：

- Visual Novel / ADV / AVG
- Sound Novel、Kinetic Novel
- 乙女、BL、百合、拔作等子类型
- 有明确剧情阅读体验的混合类型

暂不收录或标记排除：

- 纯模拟、经营、动作游戏
- 只有少量文字冒险要素的 RPG
- 无法确认类型的条目

### 4.2 VNDB：主数据源

用途：

- 日文/罗马音标题、别名
- 标签及权重
- 开发商、发行日期、平台、语言
- 游戏时长、评分、投票数
- 相关作品
- 封面

接入方式：

- API：`https://api.vndb.org/kana`
  - 初期按投票数导入 Top N
  - 限流约 200 请求 / 5 分钟
- Dump：后续全量导入使用官方 dump
- 许可：ODbL + DbCL；图片和部分描述有单独版权限制

### 4.3 Bangumi：中文补充源

用途：

- 中文标题、中文简介
- 中文标签
- 中文评分和排名
- 中文搜索
- 国产/同人 AVG 补充

接入方式：

- `GET /v0/subjects?type=4&sort=rank`
- `POST /v0/search/subjects`
- 必须设置带开发者 ID 和应用名的 User-Agent
- 搜索 API 为实验性，需要缓存和容错

### 4.4 手工录入

支持：

- 完全手工创建作品
- 关联 VNDB/Bangumi ID
- 覆盖标题、简介、封面等字段

同步策略：

- 外部数据只更新外部字段
- 手工字段优先
- 记录来源和更新时间

---

## 5. 推荐算法

### 5.1 第一版：内容推荐

目标：冷启动可用、结果可解释。

特征：

- VNDB 标签 TF-IDF 向量
- 标签权重、剧透等级
- 开发商
- 发行年代
- 游戏时长
- VNDB / Bangumi 评分和投票数
- NSFW 标记

用户画像：

- 高评分作品 → 正向权重
- 低评分作品 → 负向权重
- 收藏/玩过 → 额外权重
- “不感兴趣” → 硬过滤

打分：

```text
score = 0.55 * 内容相似度
      + 0.15 * 开发商相似度
      + 0.10 * 年代/时长接近度
      + 0.15 * 口碑质量
      + 0.05 * 新鲜度
      - 0.35 * 负向相似度
```

排序后使用 MMR 做多样性控制，避免全是同一标签。

推荐理由：

- 共同标签
- 相似的高分作品
- 同一开发商
- 外部评分/投票数

### 5.2 第二版：混合推荐

后续加入：

- VNDB votes dump 的协同过滤
- Item-CF / ALS
- 内容 + 协同 + 质量混合排序
- 探索/利用平衡
- 序列推荐（基于最近玩过的作品）

### 5.3 评估

- 留出个人 20% 评分做离线测试
- Recall@20、NDCG@20
- 标签多样性、目录覆盖率
- 人工判断：推荐 20 部里真正想玩的数量
- 记录算法版本与推荐快照

---

## 6. API 设计（第一版）

```text
GET    /api/health
GET    /api/works                 搜索/筛选/分页
GET    /api/works/{id}            作品详情
GET    /api/works/{id}/similar    相似作品
GET    /api/tags                  标签列表
GET    /api/recommendations       推荐列表
GET    /api/me/entries            我的游戏库
PUT    /api/me/entries/{work_id}  更新状态/评分/收藏
DELETE /api/me/entries/{work_id}  移除
POST   /api/feedback              不感兴趣等反馈
GET    /api/settings              阅读本地设置
PUT    /api/settings              更新本地设置
POST   /api/admin/import/vndb     导入 VNDB
POST   /api/admin/import/bangumi  导入 Bangumi
POST   /api/admin/works           手工创建作品
GET    /api/admin/sync-runs       同步记录
```

单用户模式，不做登录鉴权。

---

## 7. 实施路线图

### Phase 0：项目清理与数据底座（已完成）

- [x] 明确个人向定位
- [x] 确定 Python + FastAPI + SQLite 技术路线
- [x] 建立目录结构
- [x] 设计并创建核心数据表
- [x] 修复前端 TypeScript 构建错误
- [x] 加入基础测试与运行说明

### Phase 1：数据导入与作品库（完成）

- [x] VNDB 客户端与解析
- [x] Bangumi 客户端与解析
- [x] 手工录入
- [x] 标题、标签、公司、外部 ID 入库
- [x] 作品列表、详情、标签 API
- [x] 增量同步与定时任务（游标存 app_meta；`python -m app.scheduler --once/--interval-hours 24`）
- [x] 重复作品人工合并（候选检测 + 选择保留方合并 + 审计快照）
- [x] 标签中文化/别名映射（82 条内置映射，中文名/别名统一归一，可按中文检索）

### Phase 2：个人游戏库与内容推荐（完成）

- [x] 我的状态/评分/收藏/备注
- [x] 内容相似度推荐
- [x] MMR 多样性
- [x] 推荐理由
- [x] 不感兴趣反馈
- [x] 前端接入新 API（24 个端点，已替换旧 mock 契约）
- [x] 冷启动引导页体验优化（独立 `/onboarding` 三步流程，≥3 部才算建立画像）

### Phase 3：协同过滤与混合排序（完成）

- [x] 导入 VNDB votes dump（独立 `data/votes.db`，`scripts/import_votes.py`）
- [x] Item-CF（调整余弦 + topK 稀疏邻居，无 numpy/scipy 依赖；未实现 ALS）
- [x] 混合排序（`algorithm=auto|content|hybrid`，无 votes 数据自动降级）
- [x] 离线评估脚本（`scripts/evaluate.py`，Recall@20 / NDCG@20 / 多样性 / 覆盖率）

### Phase 4：体验与数据质量（完成）

- [x] 前端页面重构（六页路由、统一布局、组件化卡片）
- [x] 中文搜索优化（中文别名/罗马音/标签中文名检索 + 相关性排序 + 搜索建议；未引入分词与拼音）
- [x] 封面缓存（IndexedDB 缓存 + 懒加载 + 跨域优雅降级 + 占位图）
- [x] NSFW/平台/语言过滤 UI（探索页多维筛选 + 设置页全局设置）
- [x] 重复作品合并 UI（候选对、详情对比、选择保留方、二次确认）
- [x] 备份/恢复（SQLite 一致性备份、自动前置备份、路径穿越防护）

---

## 8. 验收标准

### Phase 1 验收

- 可通过命令导入至少 100 部 VNDB 作品
- 可导入 Bangumi 条目（网络允许时）
- 可手工新增作品
- API 可按关键词、标签、状态筛选作品
- 数据重复导入不会产生重复作品

### Phase 2 验收

- 给一部作品评分后，推荐结果发生变化
- 已玩/已弃坑/不感兴趣的作品不会出现在推荐中
- 每条推荐至少有一条可读的推荐理由
- 推荐结果具备基本多样性，不是同一标签刷屏
- `pytest` 全部通过

---

## 9. 风险与合规

- **VNDB API 限流**：批量导入使用 dump 或分批任务
- **Bangumi API 实验性**：缓存、重试、User-Agent 合规
- **数据许可**：VNDB 数据 ODbL/DbCL；图片、简介可能有单独版权
- **NSFW 内容**：默认过滤，可手动开启
- **重复作品**：跨源匹配先做标题精确/别名匹配，后续人工合并
- **冷启动**：先选择喜欢的作品，再逐步建立画像
- **个人偏见**：单用户评估容易过拟合，保留人工判断与留出集

---

## 10. 当前实施记录

- 2026-11-25：创建计划文档，开始将主运行链路迁移到 `gal-love-core`
- 2026-11-25：实现 SQLite 数据层、VNDB/Bangumi 导入、内容推荐、API 与测试
- 2026-11-25：修复前端 `vue-tsc` 构建错误，使 `npm run build` 通过
- 2026-11-25：按模块分派并行开发，补齐 Phase 1–4 余项：数据底座（合并/标签/搜索/备份）、增量同步与调度、votes/Item-CF/混合排序与评估、后端 API 扩展、前端契约文档、探索页搜索筛选、冷启动引导、设置页数据治理、封面缓存与详情增强
- 2026-11-25：集成验证：后端 67 项 `pytest` 通过（1 条 Starlette 弃用告警），前端 `npm run build` 通过；顶层推荐版本字段改为返回本次实际执行的算法版本
- 2026-11-25：实际运行后修复两处问题：`init_db` 幂等回填旧标签的中文名/别名（否则已有库搜不到中文标签）；重复检测不再把「同公司同年」当作独立强信号（原会把《命运石之门》与《装甲恶鬼村正》误判为重复）。联调确认 Vite `/api` 代理、中文搜索（恋爱命中 10 部）、标签筛选、备份与 OpenAPI（22 路径/24 操作）均正常
- 2026-11-25：数据扩量：VNDB 按票数从 Top 120 扩到 Top 3000，导入 3000 条（新增 2900+，0 失败），最终 2962 部作品 / 14019 条标题 / 2759 个标签 / 187288 条作品-标签关系 / 1122 家公司；导入前自动备份。Bangumi 因本地代理 502 暂不可达；VNDB dumps 站点 503，votes 数据仍未导入。大数据量下接口冒烟正常（推荐约 0.5 秒）。
- 后续可选：ALS 协同过滤、中文分词/拼音检索、封面本地代理缓存（当前为浏览器 IndexedDB 缓存，跨域图源无 CORS 时不缓存）、Bangumi 中文数据补充（待网络）、VNDB votes dump（待 dumps 站点恢复）
