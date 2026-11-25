# 代号G · Core

个人向视觉小说 / AVG 推荐系统「代号G」的数据与算法核心。

详细产品与技术计划见仓库根目录的 [`PLAN.md`](../PLAN.md)。

## 快速开始

```bash
cd gal-love-core
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 导入 VNDB 热门作品（默认 100 部）
python scripts/import_vndb.py --limit 100

# 启动 API
uvicorn app.main:app --reload --port 8000
```

API 文档：<http://localhost:8000/docs>

## 常用命令

```bash
# 导入 VNDB
python scripts/import_vndb.py --limit 300 --min-votes 50

# 导入 Bangumi
set GAL_LOVE_BANGUMI_UA=your-name/gal-love-personal/0.1
python scripts/import_bangumi.py --limit 100

# 查看推荐
python scripts/recommend.py --limit 20

# 运行测试
pytest -q
```

## 数据与许可

- VNDB 数据来自 <https://vndb.org>，遵循 ODbL / DbCL。
- Bangumi 数据来自 <https://bgm.tv>，使用其公开 API。
- 本项目仅用于个人学习与自用，不构成商业服务。
- 封面图片默认只保存外链，不批量下载。
