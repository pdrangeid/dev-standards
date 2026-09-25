"""SessionHeader / SessionLedger model rules."""

import datetime as dt

import pytest
from pydantic import ValidationError

from dev_standards.session_schema.models import (
    CheckResult,
    SessionHeader,
    SessionLedger,
)


def header(**overrides) -> dict:
    data = {
        "schema_version": 1,
        "id": "2026-09-25-topic",
        "title": "Title",
        "status": "draft",
        "created": "2026-09-25",
        "repos": [{"name": "dev-standards", "role": "primary"}],
    }
    data.update(overrides)
    return data


def test_minimal_header_is_valid_with_default_links():
    h = SessionHeader.model_validate(header())
    assert h.created == dt.date(2026, 9, 25)
    assert h.links.depends_on == [] and h.links.split_from is None


@pytest.mark.parametrize(
    "overrides, fragment",
    [
        ({"schema_version": 2}, "schema_version"),
        ({"created": "2026-09-24"}, "created must equal the date prefix"),
        ({"id": "09-25-2026-topic"}, "id"),
        ({"id": "2026-09-25-Topic"}, "id"),
        ({"status": "blocked"}, "status_reason is required"),
        ({"status": "abandoned"}, "status_reason is required"),
        ({"status": "done"}, "status"),
        ({"repos": []}, "repos"),
        (
            {"repos": [{"name": "a", "role": "secondary"}]},
            "exactly one repo must have role: primary",
        ),
        ({"stauts": "draft"}, "Extra inputs are not permitted"),
        ({"links": {"depends_on": ["not-qualified"]}}, "links.depends_on"),
    ],
)
def test_header_rejects(overrides, fragment):
    with pytest.raises(ValidationError) as exc:
        SessionHeader.model_validate(header(**overrides))
    assert fragment in str(exc.value)


def test_blocked_with_reason_is_valid():
    SessionHeader.model_validate(header(status="blocked", status_reason="waiting"))


def test_cross_file_session_links_are_accepted():
    h = SessionHeader.model_validate(
        header(
            links={
                "depends_on": ["lifeos-hostops/2026-09-18-known-hosts-bug"],
                "split_from": "dev-standards/2026-09-20-workspace-module",
            }
        )
    )
    assert h.links.split_from == "dev-standards/2026-09-20-workspace-module"


def dec(**kw) -> dict:
    return {"id": "D1", "text": "t", "status": "accepted", "origin": "user", **kw}


def test_empty_ledger_is_valid():
    assert SessionLedger.model_validate({}).runs == []


def test_cross_file_answer_needs_no_local_target():
    ref = "lifeos-hostops/2026-09-18-cranston-live-known-hosts-merge-and-docker-null#Q2"
    led = SessionLedger.model_validate({"decisions": [dec(answers=[ref])]})
    assert led.decisions[0].answers == [ref]


def test_decision_answering_local_question_resolves_it():
    SessionLedger.model_validate(
        {
            "decisions": [dec(answers=["#Q1"])],
            "questions": [{"id": "Q1", "text": "q", "status": "resolved"}],
        }
    )


def test_resolved_question_with_resolution_text_is_valid():
    SessionLedger.model_validate(
        {
            "questions": [
                {"id": "Q1", "text": "q", "status": "resolved", "resolution": "x"}
            ]
        }
    )


def test_carried_decision_with_source_is_valid():
    SessionLedger.model_validate(
        {
            "decisions": [
                dec(origin="carried", carried_from="dev-standards/2026-09-20-x#D3")
            ]
        }
    )


@pytest.mark.parametrize(
    "ledger, fragment",
    [
        ({"decisions": [dec(), dec()]}, "duplicate item ids"),
        ({"decisions": [dec(origin="carried")]}, "carried_from is required"),
        ({"decisions": [dec(carried_from="x/2026-09-20-y#D1")]}, "carried_from"),
        ({"decisions": [dec(answers=["#Q9"])]}, "same-file refs do not resolve"),
        ({"decisions": [dec(supersedes=["#D7"])]}, "same-file refs do not resolve"),
        ({"decisions": [dec(answers=["Q1"])]}, "answers"),
        ({"decisions": [dec(answers=["repo#Q1"])]}, "answers"),
        ({"decisions": [dec(id="X1")]}, "decisions.0.id"),
        ({"decisions": [dec(adr="ADR-12")]}, "adr"),
        ({"decisions": [dec(status="superseded")]}, "status"),
        (
            {"questions": [{"id": "Q1", "text": "q", "status": "resolved"}]},
            "Q1 is resolved but has no resolution",
        ),
        ({"checks": [{"id": "C1", "text": "t", "result": "fail"}]}, "reason"),
        ({"checks": [{"id": "C1", "text": "t", "result": "not_run"}]}, "reason"),
        ({"debt": [{"id": "T1", "text": "t", "scope": "other_repo"}]}, "target_repo"),
        (
            {"runs": [{"date": "2026-09-25", "surface": "vim", "summary": "s"}]},
            "surface",
        ),
        (
            {
                "runs": [
                    {
                        "date": "2026-09-25",
                        "surface": "web",
                        "summary": "s",
                        "commits": ["ed77f12"],
                    }
                ]
            },
            "commits",
        ),
        ({"produced": [{"kind": "shell_script", "ref": "x"}]}, "kind"),
        ({"decison": []}, "Extra inputs are not permitted"),
    ],
)
def test_ledger_rejects(ledger, fragment):
    with pytest.raises(ValidationError) as exc:
        SessionLedger.model_validate(ledger)
    assert fragment in str(exc.value)


def test_check_defaults_to_pending_and_pass_value_is_pass():
    led = SessionLedger.model_validate(
        {
            "checks": [
                {"id": "C1", "text": "t"},
                {"id": "C2", "text": "t", "result": "pass"},
            ]
        }
    )
    assert [c.result for c in led.checks] == [CheckResult.pending, CheckResult.passed]


@pytest.mark.parametrize(
    "surface", ["claude-code-cloud", "web", "human", "claude-code-ide@cranston-llm"]
)
def test_surfaces(surface):
    SessionLedger.model_validate(
        {"runs": [{"date": "2026-09-25", "surface": surface, "summary": "s"}]}
    )
