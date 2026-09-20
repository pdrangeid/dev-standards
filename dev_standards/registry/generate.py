"""Generate or refresh one repo's registry file from its own documentation.

The LLM is only asked to *describe* the repo; it never touches files. We validate its
stdout against the schema, force ``repo`` from the directory name, stamp
``generated_from``, and only then write — so a bad response can never corrupt an
existing registry file.

Idempotency: an LLM will not phrase things identically twice, so ``generate`` skips
the call entirely when the hash of the source docs (plus prompt version) matches the
``generated_from`` already in the file.
"""

import hashlib
import logging
import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .models import (
    RegistryError,
    RepoEntry,
    load_entry,
    parse_mapping,
    registry_filename,
    render_entry,
    validate_entry,
)

logger = logging.getLogger(__name__)

# Docs the LLM reads, in prompt order. claude.md is the legacy name of AGENTS.md.
INPUT_DOCS = [
    "README.md",
    "ARCHITECTURE.md",
    "AGENTS.md",
    "claude.md",
    "pyproject.toml",
    "docs/usage_instructions.md",
]
MAX_DOC_CHARS = 60_000
PROMPT_VERSION = "1"  # bump when the prompt changes so registries regenerate
LLM_CMD_ENV = "DEV_STANDARDS_REGISTRY_LLM_CMD"
# The prompt arrives on stdin. Any CLI that reads a prompt on stdin and prints the
# answer works (e.g. `gemini --skip-trust -p "Respond to the request above."`).
DEFAULT_LLM_CMD = "claude -p"
LLM_TIMEOUT_SEC = 300

PROMPT = """\
You are documenting a software repository for a machine-readable registry.

Analyze the documents below for the repository "{repo}" and reply with ONLY one YAML
mapping (no prose, no markdown fences) with exactly these keys:

purpose: one sentence stating why this repo exists
interfaces: list of the public functions, CLI commands or APIs it exposes
contracts: list of the data models, classes or schemas it defines or shares
integration_points:
  env: list of environment variable names it reads
  config: list of config key names it reads (schemata.yaml or a local yaml)
  deps: list of other repos in this ecosystem that it depends on
model_prefs: preferred LLM and the specific task it is used for, or "None"

Rules: quote every string; use [] when a list has nothing to report; only name things
that appear in the documents; do not include a "repo" key.

{documents}
"""


@dataclass(frozen=True)
class GenerateResult:
    """Outcome of one ``generate_entry`` call."""

    path: Path
    status: str  # "created" | "updated" | "unchanged" | "skipped"


def resolve_llm_cmd(override: str | None = None) -> list[str]:
    """LLM command as argv: explicit option, then env var, then ``claude -p``."""
    raw = override or os.environ.get(LLM_CMD_ENV) or DEFAULT_LLM_CMD
    argv = shlex.split(raw)
    if not argv:
        raise RegistryError("LLM command is empty")
    return argv


def collect_inputs(repo_root: Path) -> dict[str, str]:
    """Return ``{relative path: text}`` for each documentation file that exists."""
    found: dict[str, str] = {}
    for rel in INPUT_DOCS:
        path = repo_root / rel
        if not path.is_file():
            logger.debug(f"{repo_root.name}: no {rel}")
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError as e:
            logger.warning(f"Skipping unreadable {path}: {e}")
            continue
        if len(text) > MAX_DOC_CHARS:
            logger.debug(f"{rel} truncated from {len(text)} to {MAX_DOC_CHARS} chars")
            text = text[:MAX_DOC_CHARS] + "\n[... truncated ...]\n"
        found[rel] = text
    return found


def source_hash(inputs: dict[str, str]) -> str:
    """Stable hash of the prompt version and every input doc (path + content)."""
    digest = hashlib.sha256(f"prompt-v{PROMPT_VERSION}\0".encode())
    for rel in sorted(inputs):
        digest.update(f"{rel}\0{inputs[rel]}\0".encode())
    return f"sha256:{digest.hexdigest()}"


def build_prompt(repo_name: str, inputs: dict[str, str]) -> str:
    """Assemble the LLM prompt: instructions plus each document, delimited."""
    documents = "\n".join(f"=== {rel} ===\n{text}\n" for rel, text in inputs.items())
    return PROMPT.format(repo=repo_name, documents=documents)


def run_llm(argv: list[str], prompt: str) -> str:
    """Run the LLM command with the prompt on stdin; return its stdout.

    The command runs from an empty temp dir: the prompt is self-contained, and this
    keeps repo-local tool config (e.g. a ``.gemini/`` dir) from being loaded or trusted.
    """
    logger.debug(f"Running LLM command {argv[0]} ({len(prompt)} chars)")
    try:
        with tempfile.TemporaryDirectory(prefix="dev-standards-llm-") as sandbox:
            proc = subprocess.run(
                argv,
                input=prompt,
                capture_output=True,
                text=True,
                cwd=sandbox,
                timeout=LLM_TIMEOUT_SEC,
            )
    except FileNotFoundError as e:
        raise RegistryError(f"LLM command not found: {argv[0]}") from e
    except subprocess.TimeoutExpired as e:
        raise RegistryError(f"LLM command timed out after {LLM_TIMEOUT_SEC}s") from e
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-300:]
        raise RegistryError(f"LLM command exited {proc.returncode}: {tail}")
    if not proc.stdout.strip():
        raise RegistryError("LLM command produced no output")
    return proc.stdout


def _existing_hash(path: Path) -> str | None:
    """``generated_from`` of a valid existing registry file, else None."""
    if not path.is_file():
        return None
    try:
        return load_entry(path).generated_from
    except RegistryError as e:
        logger.debug(f"Existing {path.name} unusable, will regenerate: {e}")
        return None


def generate_entry(
    repo_root: Path,
    *,
    llm_cmd: list[str],
    force: bool = False,
) -> GenerateResult:
    """Write ``<repo>_registry.yaml`` at ``repo_root``, replacing any existing file."""
    repo_root = Path(repo_root).resolve()
    if not repo_root.is_dir():
        raise RegistryError(f"{repo_root} is not a directory")
    repo_name = repo_root.name
    target = repo_root / registry_filename(repo_name)

    inputs = collect_inputs(repo_root)
    if not inputs:
        raise RegistryError(
            f"{repo_name}: none of {', '.join(INPUT_DOCS)} found — nothing to analyze"
        )
    digest = source_hash(inputs)

    if not force and _existing_hash(target) == digest:
        logger.debug(f"{repo_name}: source docs unchanged; skipping LLM call")
        return GenerateResult(target, "skipped")

    raw = parse_mapping(
        run_llm(llm_cmd, build_prompt(repo_name, inputs)),
        f"LLM output for {repo_name}",
    )
    allowed = set(RepoEntry.model_fields) - {"repo", "generated_from"}
    stray = set(raw) - allowed
    if stray:
        logger.debug(f"{repo_name}: dropping unexpected LLM keys {sorted(stray)}")
    data = {k: v for k, v in raw.items() if k in allowed}
    data["repo"] = repo_name  # never trust the model for identity
    data["generated_from"] = digest
    entry = validate_entry(data, f"LLM output for {repo_name}")

    text = render_entry(entry)
    previous = target.read_text() if target.is_file() else None
    if previous == text:
        return GenerateResult(target, "unchanged")
    target.write_text(text)
    return GenerateResult(target, "created" if previous is None else "updated")
