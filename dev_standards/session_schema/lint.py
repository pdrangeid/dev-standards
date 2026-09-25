"""Session-file lint: models plus the cross-block rules JSON Schema can't express."""

import logging
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import ValidationError

from .models import (
    BlockerStatus,
    CheckResult,
    SessionHeader,
    SessionLedger,
    SessionStatus,
)
from .parse import LEDGER_HEADING, YamlBlock, line_for, parse_session

logger = logging.getLogger(__name__)

_LEGACY_STATUS = re.compile(r"^(?:Status:|\*\*Status:\*\*)", re.M)
_LEGACY_HEADING = re.compile(r"^#{1,6}[ \t]+Decisions Made This Session\b", re.M)
_FENCED = re.compile(r"^(`{3,}|~{3,}).*?^\1[ \t]*$", re.M | re.S)
# directories under .session/ that hold ADRs and archives, not session files
SKIP_DIRS = {"specs", "archive"}


class Severity(StrEnum):
    error = "error"
    warning = "warning"
    info = "info"


@dataclass
class LintIssue:
    """One lint finding against a session file."""

    severity: Severity
    rule: str
    message: str
    line: int | None = None
    path: str | None = None

    def to_dict(self) -> dict:
        return {**asdict(self), "severity": str(self.severity)}


def _model_issues(
    model: type, block: YamlBlock | None, rule: str, issues: list[LintIssue]
):
    """Validate a block against a model; one issue per Pydantic error."""
    data = block.data if block else None
    if data is None and model is SessionLedger:
        data = {}  # a blank ledger block is a valid empty ledger
    try:
        return model.model_validate(data)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"]) or "(root)"
            issues.append(
                LintIssue(
                    Severity.error,
                    rule,
                    f"{loc}: {err['msg']}",
                    line_for(block, err["loc"]),
                )
            )
    return None


def _strip_fenced(text: str) -> str:
    """Blank out fenced code blocks so quoted examples don't trip body rules."""
    return _FENCED.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def validate_session(path: Path, strict: bool = False) -> list[LintIssue]:
    """Lint one session file. ``strict`` makes a legacy (pre-schema) file an error."""
    parsed = parse_session(path)
    issues: list[LintIssue] = []

    if parsed.is_legacy:
        issues.append(
            LintIssue(
                Severity.error if strict else Severity.info,
                "legacy",
                f"{parsed.legacy_reason}; treated as a legacy session file",
                1,
            )
        )
        return _finish(path, issues)

    for block, message, line in parsed.errors:
        issues.append(LintIssue(Severity.error, f"{block}-yaml", message, line))

    header = None
    if parsed.header is not None:
        header = _model_issues(SessionHeader, parsed.header, "header-schema", issues)
        if header is not None and header.id != path.stem:
            issues.append(
                LintIssue(
                    Severity.error,
                    "id-filename",
                    f"id '{header.id}' does not match filename stem '{path.stem}'",
                    line_for(parsed.header, ("id",)),
                )
            )

    headings, fences = parsed.ledger_heading_lines, parsed.ledger_fence_lines
    if not headings:
        issues.append(
            LintIssue(Severity.error, "ledger-missing", f"no '## {LEDGER_HEADING}'")
        )
    elif len(headings) > 1:
        issues.append(
            LintIssue(
                Severity.error,
                "ledger-duplicate",
                f"{len(headings)} '## {LEDGER_HEADING}' headings (lines {headings})",
                headings[1],
            )
        )
    if not fences:
        issues.append(
            LintIssue(
                Severity.error,
                "ledger-missing",
                "no ```yaml session-ledger fence",
                headings[0] if headings else None,
            )
        )
    elif len(fences) > 1:
        issues.append(
            LintIssue(
                Severity.error,
                "ledger-duplicate",
                f"{len(fences)} session-ledger fences (lines {fences})",
                fences[1],
            )
        )
    for line in parsed.misplaced_fence_lines:
        issues.append(
            LintIssue(
                Severity.error,
                "ledger-placement",
                f"session-ledger fence is not under '## {LEDGER_HEADING}'",
                line,
            )
        )

    ledger = None
    if fences and not any(b == "ledger" for b, _, _ in parsed.errors):
        ledger = _model_issues(SessionLedger, parsed.ledger, "ledger-schema", issues)

    if header is not None and ledger is not None:
        issues.extend(_status_issues(header, ledger, parsed))

    body = _strip_fenced(parsed.body_text)
    offset = parsed.body_offset
    for m in _LEGACY_STATUS.finditer(body):
        issues.append(
            LintIssue(
                Severity.warning,
                "legacy-status-line",
                "body still has a legacy Status line; status lives in frontmatter",
                offset + body.count("\n", 0, m.start()) + 1,
            )
        )
    for m in _LEGACY_HEADING.finditer(body):
        issues.append(
            LintIssue(
                Severity.warning,
                "legacy-heading",
                f"'Decisions Made This Session' is replaced by '## {LEDGER_HEADING}'",
                offset + body.count("\n", 0, m.start()) + 1,
            )
        )
    return _finish(path, issues)


def _status_issues(header: SessionHeader, ledger: SessionLedger, parsed):
    """Rules tying header.status to ledger contents."""
    line = line_for(parsed.header, ("status",))
    open_blockers = [b for b in ledger.blockers if b.status == BlockerStatus.open]
    out: list[LintIssue] = []

    def err(rule: str, msg: str) -> None:
        out.append(LintIssue(Severity.error, rule, msg, line))

    match header.status:
        case SessionStatus.blocked if not open_blockers:
            err("status-blocked", "status is blocked but no blocker is open")
        case SessionStatus.complete:
            if not ledger.runs:
                err("status-complete", "status is complete but there are no runs")
            if ledger.outcome is None:
                err("status-complete", "status is complete but outcome is not set")
            pending = [c.id for c in ledger.checks if c.result == CheckResult.pending]
            if pending:
                err(
                    "status-complete",
                    f"status is complete but checks {pending} pending",
                )
            if open_blockers:
                ids = [b.id for b in open_blockers]
                err("status-complete", f"status is complete but blockers {ids} open")
        case SessionStatus.active if not ledger.runs:
            out.append(
                LintIssue(
                    Severity.warning,
                    "status-active",
                    "status is active but there are no runs",
                    line,
                )
            )
    return out


def _finish(path: Path, issues: list[LintIssue]) -> list[LintIssue]:
    for issue in issues:
        issue.path = str(path)
    issues.sort(key=lambda i: (i.line or 0, i.rule))
    return issues


def collect_paths(paths: list[Path]) -> list[Path]:
    """Expand directories to their session files (``*.md``, recursive).

    Skips ``_template.md`` and the ``specs/`` and ``archive/`` subtrees, which
    hold ADRs and Review Log archives rather than session files. Explicit file
    paths are always kept.
    """
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            for f in sorted(p.rglob("*.md")):
                rel = f.relative_to(p).parts
                if f.name == "_template.md" or SKIP_DIRS.intersection(rel[:-1]):
                    logger.debug(f"Skipping non-session file {f}")
                    continue
                out.append(f)
        else:
            out.append(p)
    return out
