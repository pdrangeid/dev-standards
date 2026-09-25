"""Locate the frontmatter and ledger blocks in a session file and load them.

Regex (and a line scan) only *locates* the blocks; their content is always
parsed with ``yaml.safe_load``. Headings and fences inside other fenced code
blocks (e.g. a quoted template) are ignored.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

LEDGER_HEADING = "Ledger"
_FENCE_OPEN = re.compile(r"^(?P<fence>`{3,}|~{3,})[ \t]*(?P<info>[^\n]*?)[ \t]*$")
_LEDGER_INFO = re.compile(r"^ya?ml[ \t]+session-ledger$")
_H2 = re.compile(r"^##[ \t]+(?P<title>.+?)[ \t]*#*[ \t]*$")


@dataclass
class YamlBlock:
    """One located YAML block: its loaded data plus the node tree for line lookups."""

    data: Any
    node: yaml.Node | None
    line: int  # 1-based line number of the block's first content line


@dataclass
class ParsedSession:
    """The located and YAML-loaded parts of a session file."""

    path: Path
    is_legacy: bool
    body_text: str
    legacy_reason: str | None = None
    body_offset: int = 0  # number of file lines before body_text
    header: YamlBlock | None = None
    ledger: YamlBlock | None = None
    header_line: int | None = None  # line of the opening ``---``
    ledger_heading_lines: list[int] = field(default_factory=list)
    ledger_fence_lines: list[int] = field(default_factory=list)
    # fences that are not inside the ``## Ledger`` section
    misplaced_fence_lines: list[int] = field(default_factory=list)
    # (block, message, line) for YAML syntax or structure problems
    errors: list[tuple[str, str, int | None]] = field(default_factory=list)

    @property
    def header_raw(self) -> Any:
        return self.header.data if self.header else None

    @property
    def ledger_raw(self) -> Any:
        return self.ledger.data if self.ledger else None


def _load_block(
    text: str, first_line: int, block: str, errors: list
) -> YamlBlock | None:
    """safe_load a block; record a YAML syntax error instead of raising."""
    try:
        data = yaml.safe_load(text)
        node = yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        line = first_line + mark.line if mark is not None else first_line
        errors.append((block, f"invalid YAML: {e}", line))
        return None
    return YamlBlock(data=data, node=node, line=first_line)


def line_for(block: YamlBlock | None, loc: tuple) -> int | None:
    """Best-effort 1-based line number of a Pydantic error ``loc`` within a block."""
    if block is None:
        return None
    node = block.node
    if node is None:
        return block.line
    for key in loc:
        if isinstance(node, yaml.MappingNode):
            match = next((v for k, v in node.value if k.value == str(key)), None)
        elif isinstance(node, yaml.SequenceNode) and isinstance(key, int):
            match = node.value[key] if key < len(node.value) else None
        else:
            match = None
        if match is None:
            break
        node = match
    return block.line + node.start_mark.line


def parse_session(path: Path) -> ParsedSession:
    """Split a session file into frontmatter, ledger, and body."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    errors: list[tuple[str, str, int | None]] = []

    header: YamlBlock | None = None
    body_start = 0
    if lines and lines[0] == "---":
        close = next((i for i in range(1, len(lines)) if lines[i] == "---"), None)
        if close is None:
            errors.append(("header", "frontmatter has no closing '---' line", 1))
            body_start = len(lines)
        else:
            header = _load_block("\n".join(lines[1:close]) + "\n", 2, "header", errors)
            body_start = close + 1
            # Pre-schema files often carry their own frontmatter (Status:/Date:/title:);
            # schema_version is what marks a file as conforming.
            if header is not None and not (
                isinstance(header.data, dict) and "schema_version" in header.data
            ):
                logger.debug(f"{path}: frontmatter has no schema_version, legacy")
                return ParsedSession(
                    path=path,
                    is_legacy=True,
                    body_text=text,
                    legacy_reason="frontmatter has no schema_version",
                )
    else:
        logger.debug(f"{path}: no frontmatter on line 1, treating as legacy")
        return ParsedSession(
            path=path, is_legacy=True, body_text=text, legacy_reason="no frontmatter"
        )

    parsed = ParsedSession(
        path=path,
        is_legacy=False,
        body_text="\n".join(lines[body_start:]),
        body_offset=body_start,
        header=header,
        header_line=1,
        errors=errors,
    )

    in_ledger_section = False
    fence: str | None = None  # the opening fence while inside a code block
    capture: list[str] | None = None
    capture_line = 0
    for idx in range(body_start, len(lines)):
        line, lineno = lines[idx], idx + 1
        if fence is not None:
            closing = line.strip()
            if closing.startswith(fence[0] * len(fence)) and set(closing) == {fence[0]}:
                if capture is not None:
                    if parsed.ledger is None:
                        parsed.ledger = _load_block(
                            "\n".join(capture) + "\n", capture_line, "ledger", errors
                        )
                    capture = None
                fence = None
            elif capture is not None:
                capture.append(line)
            continue
        opened = _FENCE_OPEN.match(line)
        if opened:
            fence = opened["fence"]
            if _LEDGER_INFO.match(opened["info"]):
                parsed.ledger_fence_lines.append(lineno)
                if not in_ledger_section:
                    parsed.misplaced_fence_lines.append(lineno)
                capture, capture_line = [], lineno + 1
            continue
        heading = _H2.match(line)
        if heading:
            in_ledger_section = heading["title"] == LEDGER_HEADING
            if in_ledger_section:
                parsed.ledger_heading_lines.append(lineno)

    if fence is not None and capture is not None:
        errors.append(("ledger", "ledger fence is never closed", capture_line - 1))
    return parsed
