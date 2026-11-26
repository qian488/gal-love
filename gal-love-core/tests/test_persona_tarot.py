from __future__ import annotations

from app.recommend import persona
from app.recommend.persona_tarot import (
    CARDS,
    KEY,
    SPREAD_POSITIONS,
    calculate,
    draw,
)
from app.repository import get_settings
from app.tag_zh import canonical_lookup

from .helpers import add_work


def _seed_works(conn) -> list[int]:
    tag_sets = [
        ["romance", "drama"],
        ["mystery", "thriller"],
        ["fantasy", "adventure"],
        ["slice of life", "comedy"],
        ["psychological", "historical"],
        ["sports", "school"],
    ]
    ids: list[int] = []
    for index, tags in enumerate(tag_sets):
        ids.append(
            add_work(
                conn,
                title=f"Tarot Work {index}",
                tags=tags,
                rating=8.0 + index * 0.1,
                year=2015 + index,
            )
        )
    return ids


def _signature(result: dict) -> list[tuple[str, bool]]:
    return [(card["id"], card["reversed"]) for card in result["cards"]]


def test_card_table_has_78_unique_cards():
    assert len(CARDS) == 78
    ids = [card["id"] for card in CARDS]
    assert len(set(ids)) == 78
    majors = [card for card in CARDS if card["id"].startswith("major-")]
    assert len(majors) == 22
    assert majors[0]["name_zh"] == "愚者"
    assert majors[-1]["name_zh"] == "世界"
    for card in CARDS:
        assert card["name"]
        assert card["name_zh"]
        assert card["themes"]
        assert card["meaning"]
        assert card["tags"]
        assert all(isinstance(weight, (int, float)) and weight > 0 for weight in card["tags"].values())


def test_card_tags_resolve_to_known_tags():
    unknown = {
        name
        for card in CARDS
        for name in card["tags"]
        if canonical_lookup(name) is None
    }
    assert unknown == set()


def test_provider_is_registered():
    module = persona.get_provider(KEY)
    assert module.KEY == "tarot"
    assert module.KIND == "draw"
    items = {item["key"]: item for item in persona.list_providers({})}
    assert items[KEY]["title"] == "塔罗一抽"
    assert items[KEY]["group"] == "play"
    assert items[KEY]["question_count"] == 0


def test_calculate_returns_empty_profile():
    result = calculate({})
    assert result["tags"] == {}
    assert result["completed"] is False
    assert result["labels"] == []


def test_same_seed_is_stable(conn):
    _seed_works(conn)
    first = draw(conn, spread=3, seed="2026-11-26")
    second = draw(conn, spread=3, seed="2026-11-26")
    assert _signature(first) == _signature(second)
    assert first["result"]["tags"] == second["result"]["tags"]
    assert [card["id"] for card in first["items"]] == [card["id"] for card in second["items"]]


def test_default_seed_falls_back_to_today(conn):
    _seed_works(conn)
    first = draw(conn, spread=1)
    second = draw(conn, spread=1)
    assert first["seed"] == second["seed"]
    assert _signature(first) == _signature(second)
    assert first["seed"]


def test_different_seed_changes_cards(conn):
    _seed_works(conn)
    signatures = {
        tuple(_signature(draw(conn, spread=3, seed=seed)))
        for seed in ("alpha", "beta", "gamma", "delta")
    }
    assert len(signatures) > 1


def test_spread_one_has_single_guidance_card(conn):
    _seed_works(conn)
    result = draw(conn, spread=1, seed="one")
    assert result["spread"] == 1
    assert len(result["cards"]) == 1
    assert result["cards"][0]["position"] == SPREAD_POSITIONS[1][0] == "今日指引"
    assert isinstance(result["items"], list)
    assert result["result"]["labels"] == [result["cards"][0]["name_zh"]]


def test_spread_three_has_three_unique_positioned_cards(conn):
    _seed_works(conn)
    result = draw(conn, spread=3, seed="three")
    cards = result["cards"]
    assert result["spread"] == 3
    assert len(cards) == 3
    assert [card["position"] for card in cards] == SPREAD_POSITIONS[3] == ["主题", "阻碍", "建议"]
    assert len({card["id"] for card in cards}) == 3


def test_invalid_spread_normalizes_to_supported_values(conn):
    _seed_works(conn)
    assert draw(conn, spread=2, seed="x")["spread"] == 1
    assert len(draw(conn, spread=0, seed="x")["cards"]) == 1
    assert draw(conn, spread=9, seed="x")["spread"] == 3


def test_reversed_cards_halve_tags_and_prefix_meaning(conn):
    _seed_works(conn)
    result = draw(conn, spread=3, seed="reversal")
    for card in result["cards"]:
        base = next(item for item in CARDS if item["id"] == card["id"])
        if card["reversed"]:
            assert card["meaning"].startswith("逆位：")
            for name, weight in base["tags"].items():
                assert card["tags"][name] == round(weight * 0.5, 4)
        else:
            assert not card["meaning"].startswith("逆位：")
            assert card["tags"] == base["tags"]


def test_draw_returns_tarot_items_without_persisting(conn):
    _seed_works(conn)
    result = draw(conn, spread=3, seed="items")
    assert isinstance(result["items"], list)
    assert result["items"]
    assert all(item["profile_source"] == "tarot" for item in result["items"])
    assert all("score" in item and "reason" in item for item in result["items"])
    assert result["result"]["tags"]
    # 塔罗不写入设置。
    profiles = get_settings(conn).get("persona_profiles") or {}
    assert KEY not in profiles
