"""Pydantic request models for the personal API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EntryUpdate(BaseModel):
    status: Literal["want", "playing", "finished", "dropped"] | None = None
    rating: float | None = Field(default=None, ge=0, le=10)
    favorite: bool | None = None
    notes: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class FeedbackCreate(BaseModel):
    work_id: int
    kind: Literal["not_interested", "like", "dislike", "seen"]
    note: str | None = None


class ManualWorkCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    title_zh: str | None = None
    original_title: str | None = None
    description: str | None = None
    cover_url: str | None = None
    release_date: str | None = None
    length_minutes: int | None = Field(default=None, ge=1)
    length_label: int | None = Field(default=None, ge=1, le=5)
    platforms: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    rating: float | None = Field(default=None, ge=0, le=10)
    nsfw: bool = False
    tags: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    titles: list[dict] = Field(default_factory=list)


class SettingsUpdate(BaseModel):
    include_nsfw: bool | None = None
    min_year: int | None = Field(default=None, ge=1900, le=2100)
    max_length_minutes: int | None = Field(default=None, ge=1)
    platform: str | None = None
    language: str | None = None
    diversity: float | None = Field(default=None, ge=0, le=0.6)
    quiz_merge_home: bool | None = None
    home_profile_sources: list[str] | None = None


class TasteQuizSubmit(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)


class PersonaSubmit(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)


class PairwiseAnswer(BaseModel):
    winner_id: int
    loser_id: int
    skipped: bool = False


class TarotDrawRequest(BaseModel):
    spread: int = Field(default=1, ge=1, le=3)
    seed: str | None = None


class ImportVndbRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=5000)
    min_votes: int = Field(default=0, ge=0)
    incremental: bool = True
    wait: bool = False


class ImportBangumiRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=2000)
    avg_only: bool = True
    incremental: bool = True
    wait: bool = False


class MergeWorksRequest(BaseModel):
    source_id: int
    target_id: int


class RestoreRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=300)


class VotesImportRequest(BaseModel):
    dump_path: str = Field(min_length=1)
    min_votes: int = Field(default=10, ge=0)
    limit: int | None = Field(default=None, ge=1)
