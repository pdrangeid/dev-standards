"""Pydantic models for the session-file frontmatter header and ``## Ledger`` block.

These models are the source of truth for the published JSON Schemas in
``schemas/``. Rules written as ``model_validator``s are enforced here and by
``session-lint`` but cannot be expressed in JSON Schema.
"""

import datetime as dt
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SCHEMA_VERSION = 1

REPO_NAME = r"[a-z0-9][a-z0-9._-]*"
SESSION_ID = r"\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*"

RepoName = Annotated[str, StringConstraints(pattern=rf"^{REPO_NAME}$")]
SessionId = Annotated[str, StringConstraints(pattern=rf"^{SESSION_ID}$")]
SessionRef = Annotated[str, StringConstraints(pattern=rf"^{REPO_NAME}/{SESSION_ID}$")]
# "#Q1" (same file) or "repo/session-id#Q1" (cross-file)
ItemRef = Annotated[
    str, StringConstraints(pattern=rf"^(?:{REPO_NAME}/{SESSION_ID})?#[DQFCTB]\d+$")
]
CommitRef = Annotated[
    str, StringConstraints(pattern=rf"^{REPO_NAME}@[0-9a-f]{{7,40}}$")
]
Surface = Annotated[
    str,
    StringConstraints(
        pattern=r"^(?:claude-code-cloud|web|human|claude-code-(?:ide|cli)@[a-z0-9.-]+)$"
    ),
]
LabelName = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Za-z0-9]*$")]
AdrRef = Annotated[str, StringConstraints(pattern=r"^ADR-\d{4}$")]


def _item_id(prefix: str):
    return Annotated[str, StringConstraints(pattern=rf"^{prefix}\d+$")]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")  # typos in keys are errors


# ---------- enums ----------
class SessionStatus(StrEnum):
    draft = "draft"
    active = "active"
    blocked = "blocked"
    complete = "complete"
    superseded = "superseded"
    abandoned = "abandoned"


class RepoRole(StrEnum):
    primary = "primary"
    secondary = "secondary"
    reference = "reference"


class DecisionStatus(StrEnum):
    proposed = "proposed"
    accepted = "accepted"
    rejected = "rejected"


class Origin(StrEnum):
    user = "user"
    agent = "agent"
    carried = "carried"


class QuestionStatus(StrEnum):
    open = "open"
    resolved = "resolved"
    deferred = "deferred"


class FindingKind(StrEnum):
    bug = "bug"
    premise_invalid = "premise_invalid"
    confirmation = "confirmation"
    drift = "drift"


class CheckResult(StrEnum):
    pending = "pending"
    passed = "pass"
    failed = "fail"
    not_run = "not_run"


class DebtScope(StrEnum):
    this_repo = "this_repo"
    other_repo = "other_repo"
    platform = "platform"


class BlockerKind(StrEnum):
    human_action = "human_action"
    environment = "environment"
    dependency = "dependency"
    decision = "decision"


class BlockerStatus(StrEnum):
    open = "open"
    cleared = "cleared"


class OutcomeStatus(StrEnum):
    met = "met"
    partial = "partial"
    not_met = "not_met"
    abandoned = "abandoned"


# ---------- header (frontmatter) ----------
class RepoRef(_Strict):
    name: RepoName
    role: RepoRole


class Links(_Strict):
    depends_on: list[SessionRef] = []
    supersedes: list[SessionRef] = []
    split_from: SessionRef | None = None
    references: list[str] = []  # free-form paths/URLs, not validated


class SessionHeader(_Strict):
    """YAML frontmatter of a session file."""

    schema_version: Literal[1]
    id: SessionId
    title: str = Field(min_length=1)
    status: SessionStatus
    status_reason: str | None = None
    created: dt.date
    repos: list[RepoRef] = Field(min_length=1)
    branch: str | None = None
    links: Links = Field(default_factory=Links)

    @model_validator(mode="after")
    def _rules(self) -> "SessionHeader":
        if self.id[:10] != self.created.isoformat():
            raise ValueError("created must equal the date prefix of id")
        if sum(r.role == RepoRole.primary for r in self.repos) != 1:
            raise ValueError("exactly one repo must have role: primary")
        if (
            self.status in (SessionStatus.blocked, SessionStatus.abandoned)
            and not self.status_reason
        ):
            raise ValueError(
                "status_reason is required when status is blocked or abandoned"
            )
        return self


# ---------- ledger items ----------
class Run(_Strict):
    date: dt.date
    surface: Surface
    model: str | None = None
    summary: str = Field(min_length=1)  # replaces free-form work-log bullets
    commits: list[CommitRef] = []


class Outcome(_Strict):
    status: OutcomeStatus
    note: str | None = None


class Decision(_Strict):
    id: _item_id("D")
    text: str = Field(min_length=1)
    status: DecisionStatus
    origin: Origin
    carried_from: ItemRef | None = None
    signoff: bool = False  # a human explicitly approved an agent decision
    answers: list[ItemRef] = []
    supersedes: list[ItemRef] = []
    adr: AdrRef | None = None

    @model_validator(mode="after")
    def _carried(self) -> "Decision":
        if (self.origin == Origin.carried) != (self.carried_from is not None):
            raise ValueError("carried_from is required iff origin is carried")
        return self


class Question(_Strict):
    id: _item_id("Q")
    text: str = Field(min_length=1)
    status: QuestionStatus
    resolution: str | None = None
    required_before: str | None = None


class Finding(_Strict):
    id: _item_id("F")
    kind: FindingKind
    text: str = Field(min_length=1)
    resolved: bool = False
    refs: list[str] = []


class Check(_Strict):
    id: _item_id("C")
    text: str = Field(min_length=1)
    command: str | None = None
    expected: str | None = None
    observed: str | None = None
    result: CheckResult = CheckResult.pending
    reason: str | None = None

    @model_validator(mode="after")
    def _reason(self) -> "Check":
        if self.result in (CheckResult.failed, CheckResult.not_run) and not self.reason:
            raise ValueError("reason is required when result is fail or not_run")
        return self


class Debt(_Strict):
    id: _item_id("T")
    text: str = Field(min_length=1)
    scope: DebtScope
    target_repo: RepoName | None = None

    @model_validator(mode="after")
    def _target(self) -> "Debt":
        if self.scope == DebtScope.other_repo and not self.target_repo:
            raise ValueError("target_repo is required when scope is other_repo")
        return self


class Blocker(_Strict):
    id: _item_id("B")
    text: str = Field(min_length=1)
    kind: BlockerKind
    owner: str = Field(min_length=1)  # "user", "agent", or a person's name
    status: BlockerStatus = BlockerStatus.open


class Artifact(_Strict):
    kind: LabelName  # intended graph label: ShellScript, MicroService, ADR, ...
    ref: str = Field(min_length=1)
    repo: RepoName | None = None


# ---------- ledger ----------
class SessionLedger(_Strict):
    """The ``yaml session-ledger`` block under ``## Ledger``."""

    runs: list[Run] = []
    outcome: Outcome | None = None
    decisions: list[Decision] = []
    questions: list[Question] = []
    findings: list[Finding] = []
    checks: list[Check] = []
    debt: list[Debt] = []
    blockers: list[Blocker] = []
    produced: list[Artifact] = []

    @model_validator(mode="after")
    def _ids_and_local_refs(self) -> "SessionLedger":
        items = [
            *self.decisions,
            *self.questions,
            *self.findings,
            *self.checks,
            *self.debt,
            *self.blockers,
        ]
        ids = [i.id for i in items]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate item ids: {sorted(dupes)}")
        known = set(ids)
        local_refs = [
            r
            for d in self.decisions
            for r in (*d.answers, *d.supersedes, d.carried_from or "")
            if r.startswith("#")
        ]
        missing = [r for r in local_refs if r[1:] not in known]
        if missing:
            raise ValueError(f"same-file refs do not resolve: {missing}")
        answered = {
            r[1:] for d in self.decisions for r in d.answers if r.startswith("#")
        }
        for q in self.questions:
            if q.status == QuestionStatus.resolved and not (
                q.resolution or q.id in answered
            ):
                raise ValueError(
                    f"{q.id} is resolved but has no resolution text and no "
                    "in-file decision answers it"
                )
        return self
