from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.db import connect
from app.main import create_app


@pytest.fixture()
def client(db_path: Path) -> TestClient:
    app = create_app(db_path)
    with TestClient(app) as test_client:
        yield test_client


def _create_work(client: TestClient, **overrides) -> dict:
    payload = {
        "title": "API Work",
        "description": "created through the API",
        "release_date": "2024-01-01",
        "rating": 8.5,
        "tags": ["romance", "school"],
        "companies": ["API Studio"],
        "platforms": ["win"],
        "languages": ["zh-Hans"],
        **overrides,
    }
    response = client.post("/api/admin/works", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_health_and_stats(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["algorithm"] == "content-v1"
    assert data["stats"]["works"] == 0
    assert client.get("/api/stats").status_code == 200


def test_manual_work_crud_and_search(client: TestClient):
    work = _create_work(client, title="API Work", title_zh="接口测试作品")
    assert work["title"] == "接口测试作品"
    work_id = work["id"]
    assert work["tags"]
    assert work["companies"] == ["API Studio"]

    listing = client.get("/api/works").json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == work_id

    assert client.get("/api/works", params={"q": "接口"}).json()["total"] == 1
    assert client.get("/api/works", params={"tag": "romance"}).json()["total"] == 1
    assert client.get("/api/works", params={"tag": "horror"}).json()["total"] == 0

    detail = client.get(f"/api/works/{work_id}")
    assert detail.status_code == 200
    assert detail.json()["description"] == "created through the API"

    assert client.get("/api/works/9999").status_code == 404


def test_entries_and_recommendations(client: TestClient):
    liked = _create_work(client, title="Liked", rating=9.0, tags=["romance", "school"])
    other = _create_work(
        client,
        title="Other",
        rating=8.4,
        tags=["romance", "school"],
        companies=["API Studio"],
    )

    response = client.put(
        f"/api/me/entries/{liked['id']}",
        json={"status": "finished", "rating": 9.5, "favorite": True},
    )
    assert response.status_code == 200
    assert response.json()["entry"]["status"] == "finished"

    entries = client.get("/api/me/entries").json()["items"]
    assert len(entries) == 1
    assert entries[0]["id"] == liked["id"]

    recs = client.get("/api/recommendations", params={"save": True}).json()
    assert recs["algorithm_version"] == "content-v1"
    assert recs["batch_id"]
    ids = [item["id"] for item in recs["items"]]
    assert liked["id"] not in ids
    assert other["id"] in ids

    similar = client.get(f"/api/works/{liked['id']}/similar").json()["items"]
    assert similar and similar[0]["id"] == other["id"]

    client.delete(f"/api/me/entries/{liked['id']}")
    assert client.get("/api/me/entries").json()["items"] == []


def test_feedback_filters_recommendations(client: TestClient):
    liked = _create_work(client, title="Liked", rating=9.0)
    disliked = _create_work(client, title="Disliked", rating=8.0)

    client.put(f"/api/me/entries/{liked['id']}", json={"rating": 9.0})
    feedback = client.post(
        "/api/feedback", json={"work_id": disliked["id"], "kind": "not_interested"}
    )
    assert feedback.status_code == 200

    ids = [item["id"] for item in client.get("/api/recommendations").json()["items"]]
    assert disliked["id"] not in ids


def test_feedback_validation(client: TestClient):
    work = _create_work(client)
    assert (
        client.post(
            "/api/feedback", json={"work_id": work["id"], "kind": "bogus"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/feedback", json={"work_id": 9999, "kind": "not_interested"}
        ).status_code
        == 404
    )


def test_settings_roundtrip(client: TestClient):
    defaults = client.get("/api/settings").json()
    assert defaults["include_nsfw"] is False

    updated = client.put(
        "/api/settings",
        json={"include_nsfw": True, "min_year": 2010, "diversity": 0.3},
    )
    assert updated.status_code == 200
    data = updated.json()
    assert data["include_nsfw"] is True
    assert data["min_year"] == 2010
    assert data["diversity"] == 0.3
    assert client.get("/api/settings").json()["min_year"] == 2010


def test_tags_endpoint(client: TestClient):
    _create_work(client, tags=["romance", "school"])
    _create_work(client, title="Second", tags=["romance"])
    tags = client.get("/api/tags").json()["items"]
    names = [tag["name"] for tag in tags]
    assert "romance" in names
    assert tags[names.index("romance")]["work_count"] == 2


def test_works_new_filters(client: TestClient):
    first = _create_work(
        client,
        title="Windows Chinese Work",
        release_date="2021-05-01",
        length_minutes=120,
        platforms=["win"],
        languages=["zh-Hans"],
    )
    second = _create_work(
        client,
        title="Switch Japanese Work",
        release_date="2015-05-01",
        length_minutes=400,
        platforms=["switch"],
        languages=["ja"],
    )

    def ids(**params) -> list[int]:
        response = client.get("/api/works", params=params)
        assert response.status_code == 200, response.text
        return [item["id"] for item in response.json()["items"]]

    assert ids(platform="win") == [first["id"]]
    assert ids(platform="switch") == [second["id"]]
    assert ids(language="zh-Hans") == [first["id"]]
    assert ids(language="ja") == [second["id"]]
    assert ids(min_year=2020) == [first["id"]]
    assert ids(max_length_minutes=200) == [first["id"]]
    assert ids(platform="win", min_year=2020, max_length_minutes=200) == [first["id"]]
    assert ids(platform="ps5") == []


def test_tags_include_zh_and_aliases(client: TestClient):
    _create_work(client, tags=["romance"])
    tag = next(item for item in client.get("/api/tags").json()["items"] if item["name"] == "romance")
    assert "name_zh" in tag
    assert isinstance(tag["aliases"], list)


def test_taste_quiz_get_and_post(client: TestClient):
    initial = client.get("/api/taste-quiz")
    assert initial.status_code == 200, initial.text
    payload = initial.json()
    assert len(payload["questions"]) == 8
    assert payload["answers"] == {}
    assert payload["result"]["completed"] is False
    assert len(payload["result"]["labels"]) == 4

    response = client.post(
        "/api/taste-quiz",
        json={
            "answers": {
                "q_story": "story_plot",
                "q_ending": "end_branch",
                "q_atmosphere": "not_an_option",
                "unknown_question": "story_plot",
            }
        },
    )
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["answers"] == {"q_story": "story_plot", "q_ending": "end_branch"}
    assert saved["result"]["tags"]["Drama"] == 1.2
    assert "多结局" in saved["result"]["labels"]
    assert saved["result"]["completed"] is False

    reloaded = client.get("/api/taste-quiz").json()
    assert reloaded["answers"] == saved["answers"]
    assert reloaded["result"] == saved["result"]
    settings = client.get("/api/settings").json()
    assert settings["quiz_answers"] == saved["answers"]
    assert settings["quiz_profile"] == saved["result"]
    assert settings["quiz_merge_home"] is True

    # 非法请求体不能变成 500。
    assert client.post("/api/taste-quiz", json={"answers": []}).status_code == 422
    assert (
        client.post("/api/taste-quiz", json={"answers": {"q_story": 123}}).status_code == 422
    )


def test_profile_source_query_validation_and_passthrough(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    assert (
        client.get("/api/recommendations", params={"profile_source": "bogus"}).status_code == 422
    )
    assert (
        client.get("/api/recommendations", params={"profile_source": "all"}).status_code == 200
    )

    _create_work(client, title="Profile Source Work")
    captured: dict = {}
    original = main.recommend

    def spy(conn, **kwargs):
        captured.update(kwargs)
        return original(conn, **kwargs)

    monkeypatch.setattr(main, "recommend", spy)
    response = client.get(
        "/api/recommendations", params={"profile_source": "quiz", "save": False}
    )
    assert response.status_code == 200, response.text
    assert captured["profile_source"] == "quiz"
    data = response.json()
    assert data["profile_source"] == "quiz"
    assert all(item["profile_source"] == "quiz" for item in data["items"])


def test_algorithm_query_validation_and_passthrough(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    assert (
        client.get("/api/recommendations", params={"algorithm": "bogus"}).status_code == 422
    )
    assert (
        client.get("/api/recommendations", params={"algorithm": "hybrid"}).status_code == 200
    )

    _create_work(client, title="Algorithm Work")
    captured: dict = {}
    original = main.recommend

    def spy(conn, **kwargs):
        captured.update(kwargs)
        return original(conn, **kwargs)

    monkeypatch.setattr(main, "recommend", spy)
    response = client.get(
        "/api/recommendations", params={"algorithm": "content", "save": False}
    )
    assert response.status_code == 200, response.text
    assert captured["algorithm"] == "content"
    assert response.json()["algorithm_version"] == "content-v1"


def test_duplicates_and_merge(client: TestClient):
    first = _create_work(
        client, title="Alpha Game", companies=["Shared Studio"], release_date="2020-02-01"
    )
    second = _create_work(
        client, title="Beta Game", companies=["Shared Studio"], release_date="2020-08-01"
    )
    shared_alias = "Shared Alias"
    db = connect(client.app.state.db_path)
    try:
        for work_id in (first["id"], second["id"]):
            db.execute(
                "INSERT INTO titles(work_id, lang, title, normalized_title, official, is_main, source) "
                "VALUES(?, '', ?, ?, 0, 0, 'manual')",
                (work_id, shared_alias, shared_alias.casefold()),
            )
        db.commit()
    finally:
        db.close()

    duplicates = client.get("/api/admin/duplicates")
    assert duplicates.status_code == 200, duplicates.text
    items = duplicates.json()["items"]
    assert items
    pair = next(
        item
        for item in items
        if {item["work_id"], item["other_id"]} == {first["id"], second["id"]}
    )
    assert pair["score"] >= 0.75
    assert pair["reasons"]

    filtered = client.get("/api/admin/duplicates", params={"min_score": 0.99}).json()["items"]
    assert filtered == []

    merged = client.post(
        "/api/admin/works/merge", json={"source_id": first["id"], "target_id": second["id"]}
    )
    assert merged.status_code == 200, merged.text
    assert merged.json()["ok"] is True
    assert merged.json()["source_id"] == first["id"]
    assert client.get(f"/api/works/{first['id']}").status_code == 404
    assert client.get(f"/api/works/{second['id']}").status_code == 200
    assert client.get("/api/admin/duplicates").json()["items"] == []


def test_merge_value_error_maps_to_400(client: TestClient):
    work = _create_work(client)
    response = client.post(
        "/api/admin/works/merge", json={"source_id": work["id"], "target_id": work["id"]}
    )
    assert response.status_code == 400
    assert "同一部" in response.json()["detail"]

    missing = client.post(
        "/api/admin/works/merge", json={"source_id": 9999, "target_id": work["id"]}
    )
    assert missing.status_code == 400


def test_backup_and_restore(client: TestClient):
    work = _create_work(client, title="Backup Work")
    assert client.get("/api/admin/backups").json()["items"] == []

    created = client.post("/api/admin/backup")
    assert created.status_code == 200, created.text
    info = created.json()
    assert info["filename"].endswith(".db")
    assert info["size_bytes"] > 0

    backups = client.get("/api/admin/backups").json()["items"]
    assert len(backups) == 1
    assert backups[0]["filename"] == info["filename"]

    restored = client.post("/api/admin/restore", json={"filename": info["filename"]})
    assert restored.status_code == 200, restored.text
    payload = restored.json()
    assert payload["ok"] is True
    assert payload["filename"] == info["filename"]
    assert payload["auto_backup"]["filename"].endswith(".db")
    assert client.get(f"/api/works/{work['id']}").status_code == 200


def test_restore_rejects_path_traversal(client: TestClient, db_path: Path):
    for filename in ("../evil.db", "..\\evil.db", str(db_path.parent / "evil.db"), "/etc/passwd"):
        response = client.post("/api/admin/restore", json={"filename": filename})
        assert response.status_code == 400, response.text
        assert client.get("/api/admin/backups").json()["items"] == []


def test_votes_stats_and_import(client: TestClient, tmp_path: Path):
    empty = client.get("/api/admin/votes/stats")
    assert empty.status_code == 200, empty.text
    assert empty.json()["available"] is False
    assert empty.json()["votes"] == 0

    missing = client.post("/api/admin/votes/import", json={"dump_path": str(tmp_path / "missing.txt")})
    assert missing.status_code == 400

    _create_work(client, title="Voted Work")
    dump = tmp_path / "votes.txt"
    dump.write_text(
        "v1 u1 80\nv1 u2 90\nv1 u3 70\nv2 u1 60\nv2 u2 50\n", encoding="utf-8"
    )
    imported = client.post(
        "/api/admin/votes/import", json={"dump_path": str(dump), "min_votes": 3}
    )
    assert imported.status_code == 200, imported.text
    data = imported.json()
    assert data["min_votes"] == 3
    assert data["items_imported"] == 1
    assert data["votes_imported"] == 3

    stats = client.get("/api/admin/votes/stats").json()
    assert stats["available"] is True
    assert stats["votes"] == 3
    assert stats["items"] == 1

    recs = client.get("/api/recommendations", params={"save": False}).json()
    assert recs["algorithm_version"] == "hybrid-v1+votes"
    assert all(item["algorithm_version"] == "hybrid-v1+votes" for item in recs["items"])


def test_votes_import_exception_maps_to_502(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    dump = tmp_path / "votes.txt"
    dump.write_text("v1 u1 80\n", encoding="utf-8")

    def boom(*args, **kwargs):
        raise RuntimeError("dump broken")

    monkeypatch.setattr(main, "import_votes_dump", boom)
    response = client.post("/api/admin/votes/import", json={"dump_path": str(dump)})
    assert response.status_code == 502
    assert "dump broken" in response.json()["detail"]


def test_vndb_wait_uses_one_run_id(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    def fake_import(conn, *, limit, min_votes, run_id, incremental):
        captured.update(
            run_id=run_id, limit=limit, min_votes=min_votes, incremental=incremental
        )
        return {"run_id": run_id, "imported": 0}

    monkeypatch.setattr(main, "import_vndb", fake_import)
    response = client.post(
        "/api/admin/import/vndb",
        json={"wait": True, "limit": 7, "min_votes": 5, "incremental": False},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["run_id"] == captured["run_id"]
    assert captured["limit"] == 7
    assert captured["min_votes"] == 5
    assert captured["incremental"] is False

    runs = client.get("/api/admin/sync-runs").json()["items"]
    assert runs[0]["id"] == captured["run_id"]
    assert runs[0]["source"] == "vndb"


def test_bangumi_wait_uses_one_run_id(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    def fake_import(conn, *, limit, avg_only, run_id, incremental):
        captured.update(run_id=run_id, limit=limit, avg_only=avg_only, incremental=incremental)
        return {"run_id": run_id, "imported": 0}

    monkeypatch.setattr(main, "import_bangumi", fake_import)
    response = client.post(
        "/api/admin/import/bangumi", json={"wait": True, "limit": 9, "avg_only": False}
    )
    assert response.status_code == 200, response.text
    assert response.json()["run_id"] == captured["run_id"]
    assert captured["avg_only"] is False
    assert captured["incremental"] is True

    runs = client.get("/api/admin/sync-runs").json()["items"]
    assert runs[0]["id"] == captured["run_id"]
    assert runs[0]["source"] == "bangumi"


def test_wait_failure_marks_run_failed(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    def boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(main, "import_vndb", boom)
    response = client.post("/api/admin/import/vndb", json={"wait": True})
    assert response.status_code == 502
    run = client.get("/api/admin/sync-runs").json()["items"][0]
    assert run["status"] == "failed"
    assert "network down" in run["error"]


def test_background_import_keeps_scheduled_shape(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured: dict = {}

    def fake_import(conn, *, limit, min_votes, run_id, incremental):
        captured.update(run_id=run_id, incremental=incremental)
        return {"run_id": run_id}

    monkeypatch.setattr(main, "import_vndb", fake_import)
    response = client.post(
        "/api/admin/import/vndb", json={"wait": False, "incremental": False}
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "scheduled"
    assert result["run_id"] == captured["run_id"]
    assert captured["incremental"] is False
