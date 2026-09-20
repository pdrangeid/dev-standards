"""Shared logging setup for the dev-standards CLI sub-apps."""

import logging


def configure_logging(debug: bool) -> None:
    """Route logs to stderr; ``--debug`` sets DEBUG, default is INFO."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
