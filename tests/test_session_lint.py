"""session-lint rules, parser edge cases, and CLI behaviour."""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dev_standards.session_schema import parse_session, validate_session
from dev_standards.session_schema.cli import lint_app
from dev_standards.session_schema.lint import collect_paths

FIXTURES = Path(__file__).parent / "fixtures" / "sessions"
MINIMAL = FIXTURES / "2026-09-25-minimal-draft.md"
runner = CliRunner()


def rules(issues, severity=None):
    return {i.rule for i in issues if severity is None or i.severity == severity}


def errors(issues):
    return [i for i in issues if i.severity == "error"]


@pytest.mark.parametrize(
    "name",
    [
        "2026-09-18-cranston-live-known-hosts-merge-and-docker-null",
        "2026-09-25-minimal-draft",
    ],
)
def test_conforming_fixtures_pass_clean(name):
    assert validate_session(FIXTURES / f"{name}.md") == []


@pytest.mark.parametrize(
    "name, rule, fragment",
    [
        ("2026-09-25-blocked-no-reason", "header-schema", "status_reason is required"),
        ("2026-09-25-blocked-no-open-blocker", "status-blocked", "no blocker is open"),
        ("2026-09-25-complete-pending-check", "status-complete", "['C1'] pending"),
        ("2026-09-25-duplicate-id", "ledger-schema", "duplicate item ids: ['D1']"),
        ("2026-09-25-carried-without-source", "ledger-schema", "carried_from"),
        ("2026-09-25-dangling-answer", "ledger-schema", "['#Q9']"),
        ("2026-09-25-resolved-unanswered", "ledger-schema", "Q1 is resolved"),
        ("2026-09-25-id-mismatch-renamed", "id-filename", "does not match filename"),
        ("2026-09-25-unknown-key", "ledger-schema", "decison"),
        ("2026-09-25-two-primary-repos", "header-schema", "exactly one repo"),
    ],
)
def test_failing_fixtures_report_exactly_their_error(name, rule, fragment):
    issues = validate_session(FIXTURES / f"{name}.md")
    errs = errors(issues)
    assert len(errs) == 1, errs
    assert errs[0].rule == rule
    assert fragment in errs[0].message


def test_legacy_file_is_info_and_error_when_strict():
    legacy = FIXTURES / "2026-06-12-assess-log-strip-embeddings.md"
    (issue,) = validate_session(legacy)
    assert (issue.severity, issue.rule, issue.line) == ("info", "legacy", 1)
    (issue,) = validate_session(legacy, strict=True)
    assert issue.severity == "error"


def test_body_status_line_is_warning_only():
    issues = validate_session(FIXTURES / "2026-09-25-legacy-status-line.md")
    assert [(i.severity, i.rule) for i in issues] == [("warning", "legacy-status-line")]
    assert issues[0].line == 19


def test_field_errors_point_at_their_line(tmp_path):
    path = tmp_path / "2026-09-25-minimal-draft.md"
    text = MINIMAL.read_text().replace(
        "decisions: []",
        "decisions:\n  - id: D1\n    text: t\n    status: maybe\n    origin: user",
    )
    path.write_text(text)
    (issue,) = validate_session(path)
    assert issue.message.startswith("decisions.0.status:")
    assert text.splitlines()[issue.line - 1].strip() == "status: maybe"


# ---------- parser / structure edge cases ----------
def write(tmp_path, text, stem="2026-09-25-minimal-draft"):
    path = tmp_path / f"{stem}.md"
    path.write_text(text)
    return path


def test_blank_ledger_block_is_an_empty_ledger(tmp_path):
    text = MINIMAL.read_text()
    start = text.index("```yaml session-ledger\n") + len("```yaml session-ledger\n")
    path = write(tmp_path, text[:start] + "```\n")
    assert validate_session(path) == []


def test_quoted_template_inside_a_fence_is_ignored(tmp_path):
    quoted = (
        "\n~~~markdown\n## Ledger\n\n```yaml session-ledger\nruns: []\n```\n"
        "Status: draft\n## Decisions Made This Session\n~~~\n"
    )
    text = MINIMAL.read_text().replace(
        "## Instructions\n", quoted + "\n## Instructions\n"
    )
    path = write(tmp_path, text)
    parsed = parse_session(path)
    assert len(parsed.ledger_heading_lines) == 1
    assert len(parsed.ledger_fence_lines) == 1
    assert validate_session(path) == []


def test_missing_ledger(tmp_path):
    text = MINIMAL.read_text()
    path = write(tmp_path, text[: text.index("## Ledger")])
    assert rules(validate_session(path)) == {"ledger-missing"}


def test_duplicate_ledger_heading_and_fence(tmp_path):
    text = MINIMAL.read_text()
    path = write(tmp_path, text + "\n" + text[text.index("## Ledger") :])
    issues = validate_session(path)
    assert [i.rule for i in errors(issues)] == ["ledger-duplicate", "ledger-duplicate"]


def test_fence_outside_ledger_section(tmp_path):
    text = MINIMAL.read_text().replace("## Ledger\n", "## Something Else\n")
    assert "ledger-placement" in rules(validate_session(write(tmp_path, text)))


def test_old_heading_is_warned(tmp_path):
    text = MINIMAL.read_text().replace(
        "## Instructions", "## Decisions Made This Session\n\n## Instructions"
    )
    issues = validate_session(write(tmp_path, text))
    assert [(i.severity, i.rule) for i in issues] == [("warning", "legacy-heading")]


def test_unclosed_frontmatter(tmp_path):
    path = write(tmp_path, "---\nschema_version: 1\n# no close\n")
    assert "header-yaml" in rules(validate_session(path))


def test_invalid_ledger_yaml_is_reported_not_raised(tmp_path):
    text = MINIMAL.read_text().replace("runs: []", "runs: [unclosed")
    assert rules(validate_session(write(tmp_path, text)), "error") == {"ledger-yaml"}


def test_active_without_runs_warns(tmp_path):
    text = MINIMAL.read_text().replace("status: draft", "status: active")
    issues = validate_session(write(tmp_path, text))
    assert [(i.severity, i.rule) for i in issues] == [("warning", "status-active")]


def test_complete_with_nothing_lists_each_gap(tmp_path):
    text = MINIMAL.read_text().replace("status: draft", "status: complete")
    text = text.replace(
        "blockers: []", "blockers:\n  - {id: B1, text: b, kind: decision, owner: user}"
    )
    msgs = [i.message for i in validate_session(write(tmp_path, text))]
    assert any("no runs" in m for m in msgs)
    assert any("outcome is not set" in m for m in msgs)
    assert any("['B1'] open" in m for m in msgs)


# ---------- path collection + CLI ----------
def test_collect_paths_skips_templates_adrs_and_archive(tmp_path):
    session = tmp_path / ".session"
    for rel in [
        "_template.md",
        "2026-09-25-a.md",
        "specs/adr/0001-x.md",
        "specs/adr/index.md",
        "archive/review-log-2026.md",
        "nested/2026-09-25-b.md",
    ]:
        (session / rel).parent.mkdir(parents=True, exist_ok=True)
        (session / rel).write_text("x")
    found = [p.relative_to(session).as_posix() for p in collect_paths([session])]
    assert found == ["2026-09-25-a.md", "nested/2026-09-25-b.md"]


def test_cli_exit_codes_and_json(tmp_path):
    ok = runner.invoke(lint_app, [str(MINIMAL)])
    assert ok.exit_code == 0, ok.output

    for name in ("2026-09-25-duplicate-id.md", "2026-09-25-legacy-status-line.md"):
        shutil.copy(FIXTURES / name, tmp_path)
    bad = runner.invoke(lint_app, [str(tmp_path), "--format", "json"])
    assert bad.exit_code == 1
    payload = json.loads(bad.stdout[bad.stdout.index("[") :])
    assert {(i["severity"], i["rule"]) for i in payload} == {
        ("error", "ledger-schema"),
        ("warning", "legacy-status-line"),
    }


def test_cli_warnings_alone_exit_zero():
    result = runner.invoke(
        lint_app, [str(FIXTURES / "2026-09-25-legacy-status-line.md")]
    )
    assert result.exit_code == 0


def test_cli_strict_fails_legacy():
    legacy = str(FIXTURES / "2026-06-12-assess-log-strip-embeddings.md")
    assert runner.invoke(lint_app, [legacy]).exit_code == 0
    assert runner.invoke(lint_app, [legacy, "--strict"]).exit_code == 1


def test_cli_missing_path_fails(tmp_path):
    assert runner.invoke(lint_app, [str(tmp_path / "nope.md")]).exit_code == 1
