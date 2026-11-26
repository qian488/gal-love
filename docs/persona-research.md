# 用户画像获取方式调研

面向「代号G」的推荐系统，评估除现有 8 题四轴口味问答之外，还能用哪些方式获取用户画像。

## 0. 结论摘要

| 方式 | 科学性 / 稳定性 | 与推荐的同构度 | 题目与维护成本 | 建议定位 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| 作品二选一（pairwise） | 高（直接来自真实偏好） | 极高（直接产出标签权重） | 低（无需题库） | 主画像来源 | P1 |
| 玩家动机画像（Quantic 简化） | 较高（25 万样本，跨区域因子一致） | 高（维度本身就是玩法偏好） | 中（8 维 × 3 题 + 映射） | 认真版问卷 | P2 |
| 九型人格（9 型 + 侧翼） | 中低（结构丰富，实证弱） | 中高（可映射到题材/基调） | 中高（27 题 + 18 组合映射） | 趣味 + 深度入口 | P3 |
| 大五人格（BFI-10 / IPIP-20） | 高（重测 0.8+，跨 50+ 文化） | 中（需二次映射到题材） | 中（10–20 题） | 学术背书版 | P4 |
| MBTI（现有四轴做法） | 低（重测 0.56–0.72，35–50% 五周内翻型） | 高（已落地） | 低（已有） | 保留，作为形式而非诊断 | 已有 |
| 情境式问卷（galgame 专用） | 中（贴近场景，难验证） | 高 | 中（写 8–12 个情境） | 现有问卷的升级方向 | P2 备选 |
| 十二星座 | 无（巴纳姆效应） | 中（可硬映射） | 极低（生日即可） | 趣味玩法，低权重 | P5 |
| 塔罗牌 | 无（随机） | 中（可硬映射） | 低中（78 张映射表） | 一次性玩法，不入画像 | P5 |
| Bartle 四型 | 低（模型古老、粒度粗） | 中 | 低（4 题） | 可并入动机问卷 | 不做独立入口 |

一句话结论：**真正值得做成"画像"的是作品二选一、玩家动机、九型、大五；星座和塔罗适合做成"玩法"而不是画像。** MBTI 已有实现应当保留，但要明确它只是借了四个维度的形式，不是心理测量。

## 1. 现有链路与约束

当前推荐的核心是一个 `UserProfile`：

```python
@dataclass
class UserProfile:
    vector: dict[int, float]          # 标签 id -> 权重（已 L2 归一化）
    negative_vector: dict[int, float]
    company_weights: dict[int, float]
    liked_work_ids: list[tuple[int, float]]
    disliked_work_ids: set[int]
    year_center: float | None
    length_center: float | None
    has_profile: bool
    source: str                       # library / quiz / all
    quiz_labels: list[str]
```

这带来一个很好的性质：**任何画像方式，只要能产出「标签权重 + 年代中心 + 时长中心」，就能零改动接入推荐引擎**。`build_quiz_profile` 已经证明了这条路：

```python
quiz_profile = {
    "code": "剧情向·悬疑·快节奏·多结局",
    "labels": ["剧情向", "悬疑", "快节奏", "多结局"],
    "tags": {"Mystery": 1.4, "Thriller": 0.6, ...},
    "year_center": 2018,
    "length_center": 600,
    "completed": True,
}
```

约束条件：

- 单用户、无鉴权，画像存在 `settings` 里即可。
- 标签体系是 VNDB 英文标签（2759 个标签、18.7 万条 work_tags），中文名与别名映射已就绪。
- 推荐公式里标签相似度权重最高（0.55），所以**映射表的质量直接决定画像效果**，页面只是壳。

## 2. 各方案分析

### 2.1 作品二选一（pairwise）—— 最推荐的增量

**做法**：从库里随机取两部作品，让用户选"更想玩这部"，做 10–15 轮。

**输出**：不经过任何题库映射，直接把被选中作品的标签按 `+1`、被淘汰作品按 `-0.4` 累加，得到向量与年代/时长中心。

**优点**：

- 零题库维护，新增标签体系或扩充数据后自动受益。
- 直接反映真实偏好，不存在"我说的"和"我做的"不一致。
- 与现有 `build_profile` 的加权逻辑完全同构，可以复用同一套函数。
- 对冷启动特别有效：用户还没有游戏库记录时，10 次点击就能建出可用画像。

**注意**：

- 候选要按口碑分层抽样，否则连续出现两部冷门作品会让人无从选择。
- 需要记录避免同一部反复出现；"两部都不想玩"应作为有效信号（负向）。
- 与 `my_entries` 是同类行为数据，合并时不应重复计权。

### 2.2 玩家动机画像（Quantic Foundry 简化版）

**模型**：Quantic Foundry 用 25 万玩家样本做因子分析，得到 12 个动机、6 个簇、3 个高层簇：

- 沉浸（Immersion）：幻想 Fantasy、故事 Story
- 创造（Creativity）：设计 Design、探索 Discovery
- 动作（Action）：破坏 Destruction、刺激 Excitement
- 社交（Social）：竞争 Competition、社群 Community
- 精通（Mastery）：挑战 Challenge、策略 Strategy
- 成就（Achievement）：完成 Completion、权力 Power

高层结构：Action-Social / Immersion-Creativity / Mastery-Achievement，跨北美、南美、西欧、东欧、东南亚样本结构一致。

**galgame 裁剪**：Destruction、Competition、Strategy 在视觉小说里信号很弱，建议保留 8 维：Story、Fantasy、Design、Discovery、Challenge、Completion、Community、Excitement。每维 3 题、5 级 Likert，共 24 题；也可以做 8 题速测（每维 1 题）。

**映射示例**：

| 维度 | 高分时的标签倾向 |
| --- | --- |
| Story | Drama、Mystery、Kinetic Novel、长篇 |
| Fantasy | Fantasy、Science Fiction、School、异世界 |
| Design | Branching Plot、Multiple Endings、Customization |
| Discovery | Mystery、Time Loop、Meta、Unreliable Narrator |
| Challenge | Mystery、Puzzle、多结局收集、长篇 |
| Completion | Multiple Endings、全收集、系列作 |
| Community | 群像、Romance、Harem（多人关系） |
| Excitement | Action、Thriller、快节奏、短篇 |

**为什么值得做**：它测的就是"你想要什么样的体验"，与推荐目标同构，比人格问卷少一层翻译。

### 2.3 九型人格（9 型 + 侧翼）

**结构**：

- 9 个核心类型，各自对应核心恐惧与核心欲望：
  1 完美型（怕出错）、2 助人型（怕不被需要）、3 成就型（怕无价值）、4 自我型（怕平庸）、5 观察型（怕无能）、6 忠诚型（怕失去支撑）、7 活跃型（怕被困住）、8 领袖型（怕被控制）、9 和平型（怕冲突）。
- 三中心：腹中心 8-9-1（愤怒）、心中心 2-3-4（羞耻）、脑中心 5-6-7（恐惧）。
- 侧翼：相邻类型渲染，得到 18 种组合（如 4w3、4w5）。
- 另有健康层级 9 级、整合/解离方向（实证支持最弱，不建议使用）。

**实现**：每型 3 题、共 27 题，或 9 题速测（每型 1 题，四选一）。结果 `code: "4w5"`，前端展示"自我型 · 5 号侧翼"。

**映射示例**（可继续细化）：

| 类型 | 标签倾向 | 轴倾向 |
| --- | --- | --- |
| 1 完美型 | Drama、Serious、Philosophical | 慢热、单结局、长篇 |
| 2 助人型 | Romance、Slice of Life、Nakige | 轻松、角色向 |
| 3 成就型 | Multiple Endings、Branching Plot | 快节奏、多结局 |
| 4 自我型 | Drama、Utsuge、Tragedy | 慢热、单结局、文艺 |
| 5 观察型 | Mystery、Science Fiction、Puzzle | 慢热、长篇、解谜 |
| 6 忠诚型 | Thriller、Mystery、Suspense | 悬疑、多结局 |
| 7 活跃型 | Comedy、Action、Adventure | 快节奏、短篇 |
| 8 领袖型 | Action、Thriller、War | 快节奏、强主角 |
| 9 和平型 | Slice of Life、Comedy、Iyashikei | 轻松、慢热、治愈 |

**风险**：类型描述容易巴纳姆化，文案要写得具体、可反驳（例如"你更愿意接受一个不圆满但真实的结局"），而不是"你渴望被理解"这种放之四海皆准的句子。

### 2.4 MBTI（已有）

现状是借 MBTI 的四维形式做口味轴（叙事/氛围/节奏/结构），这是合理的用法。需要注意：

- 学术上 MBTI 重测信度约 0.56–0.72，35–50% 的人五周内至少一个维度翻面；二分法丢失程度信息，且缺少神经质维度。
- 因此不应在界面上宣称"测出你的人格"，而应表述为"你的口味倾向"。现有文案基本做到了这一点。
- 若后续要提升稳定性，可以把四轴改成连续分数展示（而不是只给四个中文标签），并在结果页允许手动微调。

### 2.5 大五人格（BFI-10 / IPIP-20）

**结构**：开放性 O、尽责性 C、外向性 E、宜人性 A、神经质 N。重测信度 0.8 以上，跨 50 多种文化可复现，是学术界主流。

**与游戏的实证关联**（可作为映射依据）：

- 外向性：与休闲、音乐、派对类正相关；与 RPG、MMORPG、策略类负相关。
- 尽责性：与模拟、竞速、体育、格斗类正相关（任务导向）。
- 开放性：与动作冒险、平台探索类正相关。

**映射到 galgame**：

| 维度 | 高分倾向 | 低分倾向 |
| --- | --- | --- |
| 开放性 | 科幻、奇幻、实验叙事、Meta、Time Loop | 校园、日常、现实题材 |
| 尽责性 | 长篇、多结局全收集、系列作 | 短篇、单线 |
| 外向性 | 群像、Harem、Comedy、热闹日常 | 单人视角、内向主角、氛围作 |
| 宜人性 | 治愈、恋爱、Nakige、低冲突 | 暗黑、复仇、背德题材 |
| 神经质 | 悬疑、恐怖、致郁、心理描写 | 轻松、治愈、低压力 |

**价值**：作为"认真版"入口，可信度最高；但需要一层到题材的翻译，映射不如动机问卷直观。

### 2.6 情境式问卷（galgame 专用）

不问"你喜欢什么标签"，而问具体情境：

> 雨夜的车站，一个陌生人把伞递给你。你更希望接下来发生——
> A. 一段缓慢升温的日常（Slice of Life / Romance）
> B. 对方其实在追踪你（Mystery / Thriller）
> C. 你发现这不是第一次见面（Time Loop / Drama）
> D. 一场荒诞的误会（Comedy）

**优点**：比抽象题更能测出真实偏好，也更有代入感；本质仍是"选项 → 标签权重"，可以完全复用现有 `calculate_profile`。

**成本**：主要在于写 8–12 个高质量情境，且要覆盖不同题材，避免所有情境都偏向悬疑或恋爱。

**建议**：不作为独立体系，而是作为现有 8 题问卷的第二套题面（同一套引擎、不同题库），或者用来替换现有题目中较抽象的部分。

### 2.7 十二星座

**做法**：用户填生日 → 太阳星座 → 12 组标签映射。零答题成本。

**映射示例**：

| 星座 | 标签倾向 |
| --- | --- |
| 白羊 | Action、快节奏、热血 |
| 金牛 | Slice of Life、美食、慢热 |
| 双子 | Comedy、对话密集、短篇 |
| 巨蟹 | Romance、Nakige、家庭 |
| 狮子 | Drama、王道、强主角 |
| 处女 | Mystery、逻辑严谨、单结局 |
| 天秤 | Romance、群像、均衡 |
| 天蝎 | Thriller、背德、暗黑 |
| 射手 | Adventure、Fantasy、开放结局 |
| 摩羯 | Drama、长篇、现实主义 |
| 水瓶 | Science Fiction、Meta、实验 |
| 双鱼 | Utsuge、梦幻、致郁 |

**定位**：趣味入口，权重压到 0.05 左右，不能主导推荐。界面上要能一眼看出是玩梗，不做科学性暗示。

### 2.8 塔罗牌

**结构**：78 张 = 22 张大阿卡纳 + 56 张小阿卡纳（权杖/圣杯/宝剑/星币，各含 Ace–10 与侍从/骑士/王后/国王），另有正逆位。

**两种用法**：

1. **抽牌选片**：抽 1–3 张，按牌义映射成推荐主题，当场给一组作品。仪式感强，适合首页"今日一抽"。
2. **写入画像**：不推荐——同一用户每次抽到的牌不同，画像会抖动。

**映射示例**：

| 牌 | 主题倾向 |
| --- | --- |
| 愚者 | Adventure、公路、开放结局 |
| 魔术师 | Fantasy、能力觉醒 |
| 女祭司 | Mystery、神秘学、隐晦叙事 |
| 皇后 | Romance、治愈、丰盈 |
| 皇帝 | 权力、政治、秩序 |
| 恋人 | Romance、三角关系、抉择 |
| 战车 | Action、竞技、热血 |
| 隐者 | 孤独、哲学、慢热 |
| 命运之轮 | Time Loop、宿命 |
| 正义 | 推理、法庭、复仇 |
| 倒吊人 | 牺牲、致郁、反转 |
| 死神 | 终结、重生、Tragedy |
| 恶魔 | 背德、欲望、暗黑 |
| 塔 | 崩坏、悲剧、冲击 |
| 星星 | 希望、治愈、Nakige |
| 月亮 | 幻觉、悬疑、不可靠叙述 |
| 太阳 | 明朗、Comedy、圆满 |
| 世界 | 完结、全年龄、群像 |

**定位**：纯玩法，不写入持久画像；如果要做"每日推荐"，用日期做种子保证当天稳定、次日更换即可。

## 3. 统一输出契约

建议把所有画像方式收敛到同一个接口，新增体系只写一个模块，不改引擎：

```python
class PersonaProvider(Protocol):
    key: str                      # "quiz" | "motivation" | "enneagram" | "bigfive" | "zodiac"
    title: str
    def questions(self) -> list[dict]: ...
    def calculate(self, answers: dict[str, str]) -> dict:
        """返回 {code, labels, tags, year_center, length_center, completed}"""
    def build_profile(self, conn, index, stored: dict) -> UserProfile: ...
```

`build_quiz_profile` 可以直接抽成通用的 `build_tag_profile(stored, index, source=key)`，因为所有体系的落地形态都是"标签名 → 标签 id → 归一化向量"。

### 3.1 设置结构

```json
{
  "persona_profiles": {
    "quiz": {"answers": {}, "profile": {}},
    "enneagram": {"answers": {}, "profile": {}},
    "motivation": {"answers": {}, "profile": {}},
    "zodiac": {"birthday": "1996-11-03", "profile": {}}
  },
  "home_profile_sources": ["library", "quiz"],
  "quiz_merge_home": true
}
```

保留 `quiz_merge_home` 作为总开关，语义不变：关闭时各入口只用各自画像，开启时首页按 `home_profile_sources` 合并。

### 3.2 合并权重

合并前每份画像已归一化，建议按可信度加权后重新归一化：

| 来源 | 权重 |
| --- | --- |
| library（游戏库行为） | 0.45 |
| pairwise（二选一结果） | 0.30 |
| quiz / motivation / enneagram / bigfive | 各 0.15，按实际存在重新分配 |
| zodiac | 0.05 |

细节：

- 权重应按题目完成度缩放（`completed` 为 false 时乘 0.6），避免半途而废的问卷压过行为数据。
- 标签向量正负可能互相抵消（九型 4 号要致郁、星座狮子要热血），加权和之后要检查模长，过小则回退到权重最高的单一来源。
- 现有 `merge_profiles` 是 0.5/0.5 硬编码，改造时改成权重字典即可。

### 3.3 前端入口

不建议在侧栏平铺 6 个入口。建议在"推荐"下保留一个"口味测试"，进入后是体系选择页：

- 快速：作品二选一（10 轮）
- 趣味：九型人格、十二星座、塔罗一抽
- 认真：玩家动机、大五人格

每个体系卡片显示"约 X 题 / 影响首页推荐"的简短说明，结果页统一展示"你的画像标签 + 为什么推荐这些"。

### 3.4 接口扩展

`GET /api/recommendations?profile_source=` 的枚举从 `auto|library|quiz|all` 扩展为：

```
auto | library | quiz | pairwise | motivation | enneagram | bigfive | zodiac | all
```

新增 `GET /api/persona/providers` 返回可用体系与题目，`GET/POST /api/persona/{key}` 读写答案。原 `/api/taste-quiz` 保留为 `quiz` 的别名，避免破坏前端。

## 4. 优先级路线

**P1 作品二选一**

- 后端：候选抽样接口 + 选择记录 → 复用 `build_profile` 的加权逻辑。
- 前端：一个两卡片对比组件，进度 1/10。
- 收益最大、成本最低，且不依赖任何题库。

**P2 玩家动机 8 维**

- 24 题（或 8 题速测），5 级 Likert。
- 只需一张 8 维到标签的映射表，维度语义与推荐天然对齐。

**P3 九型人格**

- 27 题 + 18 种组合映射，是内容工作量最大的一项，但用户点名且趣味性强。
- 建议先做 9 型速测（9 题），映射表只写 9 型，侧翼作为后续增强。

**P4 大五人格**

- BFI-10 十题即可，输出五维百分位雷达图。
- 作为"认真版"入口，映射表复用动机问卷的一部分。

**P5 星座 / 塔罗**

- 星座：生日 → 12 组映射，一天即可接入，权重压低。
- 塔罗：78 张映射表，只做一次性推荐，不写画像；用日期作种子保证当天稳定。

**明确不做**：Bartle 四型独立入口（粒度过粗，已被动机问卷覆盖）；九型的整合/解离方向（实证最弱，容易变成玄学）。

## 5. 风险与边界

- **巴纳姆效应**：九型、星座、塔罗的描述容易让所有人对号入座。文案必须具体、可反驳，且结果页要给出"为什么是这些作品"，用作品本身证明画像有效。
- **不宣称心理诊断**：所有页面统一表述为"口味倾向"，不使用"你的人格是""心理类型"等措辞。
- **稳定性**：塔罗不写入画像；星座只在生日变更时重算；MBTI 式四轴建议显示连续分数而非只给标签。
- **数据依赖**：所有映射最终落到 VNDB 标签。映射表里的标签名必须能在 `tags` 表命中，否则该权重会被静默丢弃。建议加一个校验脚本，统计每个体系的映射命中率。
- **版权**：MBTI 官方量表、Quantic Foundry 的问卷条目与玩家类型报告均受版权保护。只能参考公开的维度定义与结构自行命题，不得直接复制题目或报告文案。现有 8 题问卷的做法（自编题、借用四轴形式）是正确方向。
- **隐私**：生日属于个人信息，只存本地 settings，不上传、不展示完整日期。

## 6. 参考

- Quantic Foundry, Gamer Motivation Model（12 动机 / 6 簇 / 3 高层簇）：https://quanticfoundry.com/2015/07/20/how-we-developed-the-gamer-motivation-profile-v2/
- Quantic Foundry, 动机的三簇结构（25 万样本）：https://quanticfoundry.com?p=1787/
- Peever et al., Personality & Video Game Genre Preferences：https://eprints.qut.edu.au/59976/1/a20-peever.pdf
- 科普中国，MBTI 的重测信度与二分法问题：https://www.kepuchina.cn/article/articleinfo?ar_id=738963
- Big Five vs MBTI 信效度对比：https://bigfivepersonality.me/zh/big-five-vs-mbti
- 九型人格结构（9 型 / 三中心 / 侧翼 / 健康层级）：https://typeshub.com/zh-TW/blog/enneagram-guide-2026-05-19

## 7. 实施状态（2026-11-26）

P1–P5 已全部落地，统一入口为 `/persona`：

| 体系 | 后端模块 | 前端入口 | 状态 |
| --- | --- | --- | --- |
| 口味测试（四轴） | `persona_quiz.py` | `/persona/quiz` | 已有，迁移到统一链路 |
| 作品二选一 | `persona_pairwise.py` | `/persona/pairwise` | 已实现 |
| 玩家动机 | `persona_motivation.py` | `/persona/motivation` | 已实现 |
| 九型人格 | `persona_enneagram.py` | `/persona/enneagram` | 已实现 |
| 大五人格 | `persona_bigfive.py` | `/persona/bigfive` | 已实现 |
| 十二星座 | `persona_zodiac.py` | `/persona/zodiac` | 已实现 |
| 塔罗一抽 | `persona_tarot.py` | `/persona/tarot` | 已实现，不落库 |
| 情境式问卷 | — | — | 未做，留作现有问卷的第二套题面 |
| Bartle 四型 | — | — | 不做独立入口，已被动机问卷覆盖 |

`profile_source` 现支持 `auto / library / all / quiz / motivation / enneagram / bigfive / zodiac / pairwise / tarot`；合并权重与第 3.2 节一致。旧 `/taste-quiz` 保留为重定向。后端 191 项测试通过，前端 `npm run build` 通过，OpenAPI 29 路径 / 33 操作。
