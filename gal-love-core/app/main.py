"""FastAPI application for the personal Gal Love recommendation system."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterator

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .backup import backup_dir, create_backup, list_backups, restore_backup
from .config import settings
from .db import connect, db_session, init_db
from .ingest.bangumi import import_bangumi
from .ingest.vndb import import_vndb
from .recommend.engine import (
    ALGORITHM_VERSION,
    algorithm_version,
    recommend,
    resolve_profile_source,
    similar_works,
)
from .recommend.quiz import QUESTIONS, calculate_profile, filter_answers
from .recommend.votes import get_votes_stats, import_votes_dump
from .repository import (
    add_feedback,
    create_manual_work,
    delete_entry,
    find_duplicate_candidates,
    finish_sync_run,
    get_entries,
    get_settings,
    get_stats,
    get_sync_runs,
    get_work,
    list_tags,
    merge_works,
    save_recommendations,
    search_works,
    set_settings,
    start_sync_run,
    upsert_entry,
)
from .schemas import (
    EntryUpdate,
    FeedbackCreate,
    ImportBangumiRequest,
    ImportVndbRequest,
    ManualWorkCreate,
    MergeWorksRequest,
    RestoreRequest,
    SettingsUpdate,
    TasteQuizSubmit,
    VotesImportRequest,
)


def _db_path(request: Request) -> Path:
    return Path(request.app.state.db_path)


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(_db_path(request))
    try:
        yield conn
    finally:
        conn.close()


def _quiz_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    settings = get_settings(conn)
    return {
        "questions": QUESTIONS,
        "answers": settings.get("quiz_answers") or {},
        "result": settings.get("quiz_profile") or calculate_profile({}),
    }


def _run_vndb_import(
    db_path: str, run_id: int, limit: int, min_votes: int, incremental: bool
) -> None:
    with db_session(db_path) as conn:
        import_vndb(
            conn, limit=limit, min_votes=min_votes, run_id=run_id, incremental=incremental
        )


def _run_bangumi_import(
    db_path: str, run_id: int, limit: int, avg_only: bool, incremental: bool
) -> None:
    with db_session(db_path) as conn:
        import_bangumi(
            conn, limit=limit, avg_only=avg_only, run_id=run_id, incremental=incremental
        )


def create_app(db_path: str | Path | None = None) -> FastAPI:
    path = Path(db_path or settings.db_path)
    init_db(path)

    app = FastAPI(
        title="Gal Love Personal API",
        description="个人向视觉小说 / AVG 推荐系统的数据与推荐 API",
        version="0.1.0",
    )
    app.state.db_path = str(path)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
        return {
            "status": "ok",
            "db": str(path),
            "stats": get_stats(conn),
            "algorithm": ALGORITHM_VERSION,
        }

    @app.get("/api/stats")
    def stats(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
        return get_stats(conn)

    @app.get("/api/works")
    def works(
        q: str | None = Query(default=None, description="标题/简介/别名搜索"),
        tag: str | None = None,
        status: str | None = Query(default=None, description="want/playing/finished/dropped/none"),
        min_rating: float | None = Query(default=None, ge=0, le=10),
        platform: str | None = Query(default=None, description="平台，如 win / switch"),
        language: str | None = Query(default=None, description="语言，如 zh-Hans / ja"),
        min_year: int | None = Query(default=None, ge=1900, le=2100),
        max_length_minutes: int | None = Query(default=None, ge=1),
        sort: str = Query(default="rating", pattern="^(rating|votes|release|title|random)$"),
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        include_nsfw: bool = False,
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        return search_works(
            conn,
            query=q,
            tag=tag,
            status=status,
            min_rating=min_rating,
            platform=platform,
            language=language,
            min_year=min_year,
            max_length_minutes=max_length_minutes,
            sort=sort,
            page=page,
            limit=limit,
            include_nsfw=include_nsfw,
        )

    @app.get("/api/works/{work_id}")
    def work_detail(work_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
        work = get_work(conn, work_id)
        if not work:
            raise HTTPException(status_code=404, detail="work not found")
        return work

    @app.get("/api/works/{work_id}/similar")
    def work_similar(
        work_id: int,
        limit: int = Query(default=10, ge=1, le=50),
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        if not get_work(conn, work_id):
            raise HTTPException(status_code=404, detail="work not found")
        return {"items": similar_works(conn, work_id, limit=limit)}

    @app.get("/api/tags")
    def tags(
        q: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        return {"items": list_tags(conn, query=q, limit=limit)}

    @app.get("/api/recommendations")
    def recommendations(
        limit: int = Query(default=20, ge=1, le=50),
        include_nsfw: bool | None = None,
        min_year: int | None = Query(default=None, ge=1900, le=2100),
        max_length_minutes: int | None = Query(default=None, ge=1),
        platform: str | None = None,
        language: str | None = None,
        diversity: float | None = Query(default=None, ge=0, le=0.6),
        algorithm: str | None = Query(default=None, pattern="^(auto|content|hybrid)$"),
        profile_source: str | None = Query(default=None, pattern="^(auto|library|quiz|all)$"),
        save: bool = True,
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        source = resolve_profile_source(conn, profile_source)
        items = recommend(
            conn,
            limit=limit,
            include_nsfw=include_nsfw,
            min_year=min_year,
            max_length_minutes=max_length_minutes,
            platform=platform,
            language=language,
            diversity=diversity,
            algorithm=algorithm,
            profile_source=profile_source,
        )
        # 报告本次实际执行的算法版本，而不是“当前可用的最高版本”。
        if items:
            version = items[0].get("algorithm_version") or algorithm_version(conn)
        elif algorithm == "content":
            version = ALGORITHM_VERSION
        else:
            version = algorithm_version(conn)
        batch_id = save_recommendations(conn, items, version) if save else None
        return {
            "items": items,
            "batch_id": batch_id,
            "algorithm_version": version,
            "profile_source": source,
        }

    @app.get("/api/me/entries")
    def entries(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
        return {"items": get_entries(conn)}

    @app.put("/api/me/entries/{work_id}")
    def update_entry(
        work_id: int,
        payload: EntryUpdate,
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        if not get_work(conn, work_id):
            raise HTTPException(status_code=404, detail="work not found")
        data = payload.model_dump(exclude_unset=True)
        try:
            work = upsert_entry(conn, work_id, data)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return work or {}

    @app.delete("/api/me/entries/{work_id}")
    def remove_entry(work_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
        delete_entry(conn, work_id)
        return {"ok": True}

    @app.post("/api/feedback")
    def create_feedback(
        payload: FeedbackCreate,
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        if not get_work(conn, payload.work_id):
            raise HTTPException(status_code=404, detail="work not found")
        add_feedback(conn, payload.work_id, payload.kind, payload.note)
        return {"ok": True}

    @app.get("/api/taste-quiz")
    def taste_quiz(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
        return _quiz_payload(conn)

    @app.post("/api/taste-quiz")
    def submit_taste_quiz(
        payload: TasteQuizSubmit,
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        answers = filter_answers(payload.answers)
        result = calculate_profile(answers)
        set_settings(conn, {"quiz_answers": answers, "quiz_profile": result})
        return _quiz_payload(conn)

    @app.get("/api/settings")
    def read_settings(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
        return get_settings(conn)

    @app.put("/api/settings")
    def update_settings(
        payload: SettingsUpdate,
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        return set_settings(conn, payload.model_dump(exclude_unset=True))

    @app.post("/api/admin/works")
    def create_work(
        payload: ManualWorkCreate,
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        work_id = create_manual_work(conn, payload.model_dump())
        return get_work(conn, work_id) or {}

    @app.post("/api/admin/import/vndb")
    def start_vndb_import(
        payload: ImportVndbRequest,
        background_tasks: BackgroundTasks,
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        run_id = start_sync_run(conn, "vndb")
        if payload.wait:
            try:
                return import_vndb(
                    conn,
                    limit=payload.limit,
                    min_votes=payload.min_votes,
                    run_id=run_id,
                    incremental=payload.incremental,
                )
            except Exception as exc:  # noqa: BLE001
                finish_sync_run(conn, run_id, "failed", error=str(exc))
                raise HTTPException(status_code=502, detail=str(exc)) from exc
        background_tasks.add_task(
            _run_vndb_import,
            app.state.db_path,
            run_id,
            payload.limit,
            payload.min_votes,
            payload.incremental,
        )
        return {"status": "scheduled", "run_id": run_id}

    @app.post("/api/admin/import/bangumi")
    def start_bangumi_import(
        payload: ImportBangumiRequest,
        background_tasks: BackgroundTasks,
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        run_id = start_sync_run(conn, "bangumi")
        if payload.wait:
            try:
                return import_bangumi(
                    conn,
                    limit=payload.limit,
                    avg_only=payload.avg_only,
                    run_id=run_id,
                    incremental=payload.incremental,
                )
            except Exception as exc:  # noqa: BLE001
                finish_sync_run(conn, run_id, "failed", error=str(exc))
                raise HTTPException(status_code=502, detail=str(exc)) from exc
        background_tasks.add_task(
            _run_bangumi_import,
            app.state.db_path,
            run_id,
            payload.limit,
            payload.avg_only,
            payload.incremental,
        )
        return {"status": "scheduled", "run_id": run_id}

    @app.get("/api/admin/sync-runs")
    def sync_runs(
        limit: int = Query(default=20, ge=1, le=100),
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        return {"items": get_sync_runs(conn, limit=limit)}

    @app.get("/api/admin/duplicates")
    def duplicates(
        limit: int = Query(default=50, ge=1, le=500),
        min_score: float = Query(default=0.75, ge=0, le=1),
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        return {"items": find_duplicate_candidates(conn, min_score=min_score, limit=limit)}

    @app.post("/api/admin/works/merge")
    def merge(
        payload: MergeWorksRequest,
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> dict[str, Any]:
        try:
            return merge_works(conn, payload.source_id, payload.target_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/admin/backups")
    def backups() -> dict[str, Any]:
        return {"items": list_backups(Path(app.state.db_path))}

    @app.post("/api/admin/backup")
    def backup() -> dict[str, Any]:
        try:
            return create_backup(Path(app.state.db_path))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/admin/restore")
    def restore(payload: RestoreRequest) -> dict[str, Any]:
        db_file = Path(app.state.db_path)
        filename = payload.filename
        directory = backup_dir(db_file)
        if (
            not filename
            or "\x00" in filename
            or filename in {".", ".."}
            or Path(filename).name != filename
        ):
            raise HTTPException(status_code=400, detail="备份文件名非法：只接受 backups 目录内的文件名")
        candidate = directory / filename
        try:
            if candidate.resolve().parent != directory.resolve():
                raise ValueError("备份文件必须位于 backups 目录内")
            return restore_backup(db_file, candidate)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/admin/votes/stats")
    def votes_stats() -> dict[str, Any]:
        return get_votes_stats(Path(app.state.db_path))

    @app.post("/api/admin/votes/import")
    def votes_import(payload: VotesImportRequest) -> dict[str, Any]:
        dump = Path(payload.dump_path).expanduser()
        if not dump.is_file():
            raise HTTPException(status_code=400, detail=f"投票文件不存在或不是文件: {dump}")
        try:
            return import_votes_dump(
                dump,
                Path(app.state.db_path),
                min_votes=payload.min_votes,
                limit=payload.limit,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return app


app = create_app()
