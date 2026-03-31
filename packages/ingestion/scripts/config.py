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

# AN open data
AN_OPENDATA_ZIP: str = "https://data.assemblee-nationale.fr/static/openData/repository/17/amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip"
AN_PHOTO_BASE: str = "https://www2.assemblee-nationale.fr/static/tribun/17/photos/120"

# Senat API
SENAT_API_BASE: str = "https://www.senat.fr/api-senat"

# AN scrutins (votes)
AN_SCRUTINS_ZIP: str = "https://data.assemblee-nationale.fr/static/openData/repository/17/loi/scrutins/Scrutins.json.zip"
