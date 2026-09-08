"""Validated, versioned contracts shared by the workflow and integrations."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def uid() -> str:
    return uuid4().hex


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value) -> str:
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_default=True)


class Box(Model):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def bounds(self):
        if self.x + self.width > 1.001 or self.y + self.height > 1.001:
            raise ValueError("Box must fit inside the frame")
        return self


class Cue(Model):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[\w-]+$")
    start: float = Field(ge=0, le=86400)
    end: float = Field(gt=0, le=86400)
    text: str = Field(min_length=1, max_length=4000)
    box: Box | None = None

    @model_validator(mode="after")
    def duration(self):
        if self.end <= self.start:
            raise ValueError("Cue end must be after start")
        return self


class Asset(Model):
    id: str = Field(default_factory=uid)
    name: str = Field(min_length=1, max_length=150)
    locale: str = Field(min_length=2, max_length=20)
    kind: Literal["SUBTITLE", "SDH", "DUB", "AD"]
    parent_id: str | None = None
    # Maps a derivative's local timeline onto the master timeline.
    master_offset: float = Field(default=0, ge=-86400, le=86400)
    cues: list[Cue] = Field(min_length=1, max_length=10000)
    revision: int = 1

    @model_validator(mode="after")
    def unique_cues(self):
        if len({c.id for c in self.cues}) != len(self.cues):
            raise ValueError("Cue IDs must be unique within an asset")
        return self

    def content_hash(self):
        return digest(self.model_dump(exclude={"revision"}))


class Invariant(Model):
    id: str = Field(default_factory=uid)
    kind: Literal["NUMBER", "REVEAL", "SOUND", "DIALOGUE", "CLUE"]
    description: str = Field(min_length=1, max_length=1500)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    value: str = Field(max_length=300)
    evidence: str = Field(min_length=1, max_length=2500)
    aliases: list[str] = Field(default_factory=list, max_length=30)
    box: Box | None = None

    @model_validator(mode="after")
    def duration(self):
        if self.end <= self.start:
            raise ValueError("Invariant end must be after start")
        return self


class StorySpec(Model):
    invariants: list[Invariant] = Field(min_length=1, max_length=200)
    notes: str = Field(default="", max_length=3000)

    @model_validator(mode="after")
    def unique_invariants(self):
        if len({i.id for i in self.invariants}) != len(self.invariants):
            raise ValueError("Invariant IDs must be unique")
        return self


class Finding(Model):
    id: str = Field(default_factory=uid)
    asset_id: str
    cue_id: str | None
    invariant_id: str
    kind: str
    description: str
    evidence: str
    start: float
    end: float
    severity: Literal["ERROR", "REVIEW"] = "ERROR"


class Change(Model):
    asset_id: str
    base_hash: str
    cue_id: str
    replacement: Cue | None
    # Missing SDH events can be repaired by inserting a new cue.
    operation: Literal["REPLACE", "INSERT", "DELETE"] = "REPLACE"

    @model_validator(mode="after")
    def valid_operation(self):
        if self.operation != "DELETE" and (not self.replacement or self.replacement.id != self.cue_id):
            raise ValueError("Replacement ID must match cue ID")
        return self


class Proposal(Model):
    id: str = Field(default_factory=uid)
    finding_ids: list[str]
    spec_digest: str = ""
    changes: list[Change] = Field(min_length=1, max_length=100)
    rationale: str = Field(min_length=1, max_length=6000)
    uncertainty: str = Field(default="", max_length=3000)
    status: Literal["PROPOSED", "REJECTED", "APPLIED", "ROLLED_BACK"] = "PROPOSED"
    approved_digest: str | None = None
    approved_by: str | None = None
    snapshots: list[Asset] = Field(default_factory=list)
    result_hashes: dict[str, str] = Field(default_factory=dict)

    def approval_digest(self):
        return digest(self.model_dump(include={"id", "finding_ids", "spec_digest", "changes", "rationale", "uncertainty"}))


class Event(Model):
    at: str = Field(default_factory=now)
    action: str
    actor: str
    details: dict = Field(default_factory=dict)


class Project(Model):
    id: str = Field(default_factory=uid)
    title: str = Field(min_length=1, max_length=150)
    script: str = Field(min_length=1, max_length=100000)
    revision: int = 1
    created_at: str = Field(default_factory=now)
    media_key: str | None = None
    media_mime: str | None = None
    assets: list[Asset] = Field(default_factory=list, max_length=100)
    spec: StorySpec | None = None
    approved_spec_digest: str | None = None
    findings: list[Finding] = Field(default_factory=list)
    proposals: list[Proposal] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    status: str = "INGESTED"
    indexed_revision: int | None = None
    snapshot_id: str | None = None

    def asset(self, asset_id: str) -> Asset:
        return next(a for a in self.assets if a.id == asset_id)

    def record(self, action: str, actor="system", **details):
        self.events.append(Event(action=action, actor=actor, details=details))


def presentation_errors(asset: Asset) -> list[str]:
    errors = []
    previous = None
    for cue in sorted(asset.cues, key=lambda c: (c.start, c.end)):
        if previous and cue.start < previous.end:
            errors.append(f"{cue.id}: overlaps cue {previous.id}")
        if asset.kind in {"SUBTITLE", "SDH"}:
            clean = re.sub(r"<[^>]+>", "", cue.text)
            if len(clean.replace("\n", "")) / (cue.end - cue.start) > 25:
                errors.append(f"{cue.id}: exceeds configured 25 characters/second")
            if len(clean.splitlines()) > 2:
                errors.append(f"{cue.id}: exceeds two subtitle lines")
        previous = cue
    return errors
