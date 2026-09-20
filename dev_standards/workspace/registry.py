"""Repo registry YAML lookup — supplies each repo's one-line description."""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def _read_yaml(path: Path):
    """Parse a YAML file, returning None (with a debug note) if unusable."""
    try:
        return yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as e:
        logger.debug(f"Registry file {path} unreadable: {e}")
        return None


def lookup_purpose(repo_name: str, registry_dir: Path | None) -> str | None:
    """Return the ``purpose`` for ``repo_name`` from registry YAML, or None.

    Registry files live outside the repos, in ``registry_dir``. Two layouts exist
    in the ecosystem, tried in order: a per-repo ``<repo_name with _>_registry.yaml``
    mapping, then an aggregate ``registry.yaml`` list of ``{repo, purpose}`` entries.
    """
    if registry_dir is None:
        return None

    per_repo = registry_dir / f"{repo_name.replace('-', '_')}_registry.yaml"
    if per_repo.is_file():
        data = _read_yaml(per_repo)
        if isinstance(data, dict) and data.get("purpose"):
            return str(data["purpose"])
        logger.debug(f"{per_repo} has no usable 'purpose'; falling back")

    aggregate = registry_dir / "registry.yaml"
    if aggregate.is_file():
        data = _read_yaml(aggregate)
        if isinstance(data, list):
            for entry in data:
                if (
                    isinstance(entry, dict)
                    and entry.get("repo") == repo_name
                    and entry.get("purpose")
                ):
                    return str(entry["purpose"])
    logger.debug(f"No registry purpose for {repo_name} in {registry_dir}")
    return None
