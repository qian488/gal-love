"""Built-in VNDB English tag -> Chinese mapping and alias lookup.

The canonical names are the English names used by VNDB.  Every entry also
carries a Chinese display name and a list of common aliases (English
synonyms, Chinese synonyms and short forms).  ``canonical_lookup`` resolves
any of those spellings to the same canonical tag.
"""

from __future__ import annotations

import sqlite3

from .normalize import json_dumps, json_loads, normalize_text, unique_preserving_order

# canonical English name -> (中文名, 别名列表)
TAG_ZH_MAP: dict[str, tuple[str, list[str]]] = {
    "romance": ("恋爱", ["love", "恋爱", "爱情", "romantic"]),
    "comedy": ("喜剧", ["搞笑", "喜剧", "comical", "humor"]),
    "school": ("校园", ["校园", "学园", "school life"]),
    "fantasy": ("奇幻", ["奇幻", "魔幻", "fantasy world"]),
    "drama": ("剧情", ["剧情", "dramatic"]),
    "mystery": ("推理", ["推理", "悬疑", "mystery novel"]),
    "horror": ("恐怖", ["恐怖", "horror novel"]),
    "ero": ("色情", ["色情", "成人", "erotic", "h内容"]),
    "visual novel": ("视觉小说", ["视觉小说", "vn", "adv", "avg", "visualnovel"]),
    "kinetic novel": ("动态小说", ["动态小说", "kineticnovel"]),
    "sound novel": ("音响小说", ["音响小说", "soundnovel"]),
    "adventure": ("冒险", ["冒险", "adventure game"]),
    "action": ("动作", ["动作", "action game"]),
    "sci-fi": ("科幻", ["科幻", "scifi", "sf", "science fiction"]),
    "slice of life": ("日常", ["日常", "日常系", "生活片段", "sliceoflife"]),
    "psychological": ("心理", ["心理", "psychological thriller"]),
    "thriller": ("惊悚", ["惊悚", "thriller"]),
    "supernatural": ("超自然", ["超自然", "灵异"]),
    "magic": ("魔法", ["魔法"]),
    "mecha": ("机甲", ["机甲", "mecha"]),
    "historical": ("历史", ["历史", "historical fiction"]),
    "war": ("战争", ["战争", "war story"]),
    "sports": ("运动", ["运动", "体育", "sports"]),
    "music": ("音乐", ["音乐", "musical"]),
    "idol": ("偶像", ["偶像", "idol"]),
    "cooking": ("料理", ["料理", "烹饪", "food"]),
    "dating sim": ("恋爱模拟", ["恋爱模拟", "模拟恋爱", "datingsim"]),
    "tragedy": ("悲剧", ["悲剧", "tragic"]),
    "tearjerker": ("催泪", ["催泪", "感人"]),
    "happy ending": ("圆满结局", ["圆满结局", "happyend", "he"]),
    "multiple endings": ("多结局", ["多结局", "multiend"]),
    "time travel": ("时空穿越", ["时空穿越", "穿越", "timetravel"]),
    "amnesia": ("失忆", ["失忆", "记忆丧失"]),
    "memory manipulation": ("记忆操纵", ["记忆操纵", "记忆修改"]),
    "artificial intelligence": ("人工智能", ["人工智能", "ai"]),
    "virtual reality": ("虚拟现实", ["虚拟现实", "vr"]),
    "robot": ("机器人", ["机器人", "robot"]),
    "android": ("仿生人", ["仿生人", "android"]),
    "yuri": ("百合", ["百合", "gl", "女同性恋", "shoujo ai"]),
    "yaoi": ("BL", ["bl", "耽美", "男同性恋", "shounen ai"]),
    "otome": ("乙女", ["乙女", "otome game"]),
    "bara": ("熊系", ["熊系", "bara", "肌肉男"]),
    "crossdressing": ("女装", ["女装", "伪娘", "crossdress"]),
    "gender bender": ("性别转换", ["性别转换", "性转", "genderbend"]),
    "cosplay": ("角色扮演", ["角色扮演", "cosplay"]),
    "maid": ("女仆", ["女仆", "maid"]),
    "nurse": ("护士", ["护士", "nurse"]),
    "teacher": ("教师", ["教师", "老师", "teacher"]),
    "student": ("学生", ["学生", "student"]),
    "siblings": ("兄弟姐妹", ["兄弟姐妹", "兄妹", "sibling"]),
    "parent child": ("亲子", ["亲子", "父母", "parentchild"]),
    "friendship": ("友情", ["友情", "友谊", "friendship"]),
    "family": ("家庭", ["家庭", "family"]),
    "gore": ("血腥", ["血腥", "暴力血腥", "gore"]),
    "violence": ("暴力", ["暴力", "violence"]),
    "philosophical": ("哲学", ["哲学", "philosophy"]),
    "religion": ("宗教", ["宗教", "religion"]),
    "mythology": ("神话", ["神话", "mythology"]),
    "folklore": ("民俗", ["民俗", "传说", "folklore"]),
    "urban": ("都市", ["都市", "urban"]),
    "rural": ("乡村", ["乡村", "田园", "rural"]),
    "summer": ("夏日", ["夏日", "summer"]),
    "winter": ("冬日", ["冬日", "winter"]),
    "festival": ("祭典", ["祭典", "夏日祭", "festival"]),
    "hot springs": ("温泉", ["温泉", "onsen", "hotspring"]),
    "travel": ("旅行", ["旅行", "travel"]),
    "seaside": ("海边", ["海边", "海滨", "seaside"]),
    "space": ("太空", ["太空", "宇宙", "space"]),
    "steampunk": ("蒸汽朋克", ["蒸汽朋克", "steampunk"]),
    "cyberpunk": ("赛博朋克", ["赛博朋克", "cyberpunk"]),
    "post-apocalyptic": ("末世", ["末世", "废土", "postapocalyptic"]),
    "zombie": ("丧尸", ["丧尸", "僵尸", "zombie"]),
    "vampire": ("吸血鬼", ["吸血鬼", "vampire"]),
    "ghost": ("幽灵", ["幽灵", "鬼", "ghost"]),
    "detective": ("侦探", ["侦探", "detective story"]),
    "courtroom": ("法庭", ["法庭", "律师", "courtroom"]),
    "medical": ("医疗", ["医疗", "医生", "medical"]),
    "painting": ("绘画", ["绘画", "美术", "painting"]),
    "photography": ("摄影", ["摄影", "photography"]),
    "writing": ("写作", ["写作", "小说家", "writing"]),
    "theater": ("戏剧", ["戏剧", "舞台剧", "theater"]),
    "dance": ("舞蹈", ["舞蹈", "dance"]),
    "cafe": ("咖啡厅", ["咖啡厅", "咖啡店", "cafe"]),
    "restaurant": ("餐厅", ["餐厅", "restaurant"]),
    "cats": ("猫", ["猫", "猫咪", "cat"]),
    "dogs": ("狗", ["狗", "狗狗", "dog"]),
    "animals": ("动物", ["动物", "animal"]),
    "nature": ("自然", ["自然", "nature"]),
    "nsfw": ("成人内容", ["成人内容", "r18", "nsfw"]),
}

CanonicalInfo = tuple[str, str, list[str]]

_LOOKUP: dict[str, CanonicalInfo] = {}


def _build_index() -> None:
    for canonical, (name_zh, aliases) in TAG_ZH_MAP.items():
        info: CanonicalInfo = (
            canonical,
            name_zh,
            unique_preserving_order([name_zh, *aliases]),
        )
        for spelling in (canonical, name_zh, *aliases):
            key = normalize_text(spelling)
            if key:
                _LOOKUP[key] = info


_build_index()


def canonical_lookup(name: str | None) -> CanonicalInfo | None:
    """Resolve an English/Chinese name or alias to ``(canonical, zh, aliases)``.

    Returns ``None`` when the name is not part of the built-in mapping.
    """
    if not name:
        return None
    return _LOOKUP.get(normalize_text(name))


def canonical_lookup_keys(name: str | None) -> set[str]:
    """All normalized spellings that should resolve to the same tag."""
    info = canonical_lookup(name)
    if info is None:
        key = normalize_text(name)
        return {key} if key else set()
    canonical, name_zh, aliases = info
    keys = {normalize_text(value) for value in (canonical, name_zh, *aliases)}
    return {key for key in keys if key}


def backfill_tag_names(conn: sqlite3.Connection) -> dict[str, int]:
    """Fill translations and alias rows for tags created before the mapping existed.

    The importer applies ``canonical_lookup`` when a tag is first created, but an
    existing database keeps the old English-only rows.  This function is called
    idempotently by ``init_db`` so upgrading never needs a manual migration step.
    """
    updated = 0
    aliases_added = 0
    rows = conn.execute("SELECT id, name, aliases FROM tags").fetchall()
    for row in rows:
        info = canonical_lookup(row["name"])
        if info is None:
            continue
        canonical, name_zh, aliases = info
        current = json_loads(row["aliases"], []) or []
        merged = unique_preserving_order([*current, *aliases, name_zh])
        conn.execute(
            "UPDATE tags SET name_zh = COALESCE(name_zh, ?), aliases = ? WHERE id = ?",
            (name_zh, json_dumps(merged), row["id"]),
        )
        updated += 1
        canonical_norm = normalize_text(canonical)
        spellings = {normalize_text(value) for value in (name_zh, *aliases)}
        spellings.discard("")
        spellings.discard(canonical_norm)
        for alias_norm in spellings:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO tag_aliases(alias_normalized, tag_id, lang, source)
                VALUES(?, ?, ?, 'builtin')
                """,
                (alias_norm, row["id"], "zh" if alias_norm == normalize_text(name_zh) else ""),
            )
            aliases_added += cur.rowcount
    return {"tags_updated": updated, "aliases_added": aliases_added}
