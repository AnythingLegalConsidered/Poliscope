"""Shared utilities — logging, rate limiting, HTTP helpers."""

import io
import logging
import time
import zipfile

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

def download_zip_json_files(url: str) -> dict[str, dict]:
    """Download ZIP from *url*, extract all .json files, return {filename: parsed_json}."""
    logger.info("Downloading ZIP: %s", url)
    with httpx.Client(timeout=120) as client:
        response = client.get(url)
        response.raise_for_status()
        raw_bytes = response.content
    rate_limit()

    results: dict[str, dict] = {}
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        json_names = [n for n in zf.namelist() if n.endswith(".json")]
        logger.info("ZIP contains %d JSON files", len(json_names))
        for name in json_names:
            with zf.open(name) as f:
                import json
                results[name] = json.load(f)

    return results


def listify(v) -> list:
    """Normalize None/dict/list to list. Critical for AN mandats field."""
    if v is None:
        return []
    if isinstance(v, dict):
        return [v]
    return list(v)


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
