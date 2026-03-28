"""Shared utilities — logging, rate limiting, HTTP helpers."""

import logging
import time

import httpx

from config import REQUEST_DELAY

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def rate_limit(delay: float | None = None) -> None:
    """Sleep for *delay* seconds (defaults to REQUEST_DELAY)."""
    time.sleep(delay if delay is not None else REQUEST_DELAY)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def fetch_json(url: str, params: dict | None = None) -> dict:
    """
    GET *url*, return parsed JSON.

    Logs the URL, raises on HTTP errors, and waits REQUEST_DELAY
    after each call to respect rate limits.
    """
    logger.info("GET %s", url)
    with httpx.Client(timeout=30) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    rate_limit()
    return data
