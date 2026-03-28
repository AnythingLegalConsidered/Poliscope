"""Shared configuration — loads .env from project root."""

import os
from dotenv import load_dotenv

# Load .env from repo root (three levels up from packages/ingestion/scripts/)
_env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(_env_path)

DATABASE_URL: str = os.environ["DATABASE_URL"]
NOSDEPUTES_BASE: str = "https://www.nosdeputes.fr"
REQUEST_DELAY: float = 1.0  # seconds between API calls
LEGISLATURE: int = 17
