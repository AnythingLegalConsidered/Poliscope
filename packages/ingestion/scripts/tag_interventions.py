"""Tag parliamentary interventions using keyword matching.

Usage:
    python tag_interventions.py              # Tag untagged interventions only
    python tag_interventions.py --retag-all  # Clear and retag all interventions
"""

import argparse
import logging

from tqdm import tqdm

from db import get_connection
from tags_dictionary import TAGS_DICTIONARY, TAGS_DISPLAY_NAMES, tag_content

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 100


def ensure_tags(conn) -> dict[str, int]:
    """Insert all tags into the tags table and return {slug: id} mapping."""
    for slug, display_name in TAGS_DISPLAY_NAMES.items():
        conn.execute(
            "INSERT INTO tags (name, slug) VALUES (%s, %s) ON CONFLICT (slug) DO NOTHING",
            (display_name, slug),
        )
    conn.commit()

    cur = conn.execute("SELECT slug, id FROM tags")
    return {
        (bytes(row[0]).decode("utf-8") if isinstance(row[0], (bytes, memoryview)) else str(row[0])): row[1]
        for row in cur.fetchall()
    }


def fetch_interventions(conn, retag_all: bool):
    """Fetch interventions to tag."""
    if retag_all:
        return conn.execute("SELECT id, content FROM interventions").fetchall()
    else:
        return conn.execute(
            "SELECT id, content FROM interventions "
            "WHERE id NOT IN (SELECT DISTINCT intervention_id FROM intervention_tags)"
        ).fetchall()


def tag_interventions(retag_all: bool = False) -> None:
    """Main tagging logic."""
    with get_connection() as conn:
        # Step 1: Ensure tags exist
        slug_to_id = ensure_tags(conn)
        logger.info("Tags in DB: %d", len(slug_to_id))

        # Step 2: Clear existing tags if retag-all
        if retag_all:
            conn.execute("DELETE FROM intervention_tags")
            conn.commit()
            logger.info("Cleared all existing tag assignments (--retag-all)")

        # Step 3: Fetch interventions
        interventions = fetch_interventions(conn, retag_all)
        logger.info("Interventions to process: %d", len(interventions))

        if not interventions:
            logger.info("Nothing to tag.")
            return

        # Step 4: Tag each intervention
        total_tags = 0
        untagged = 0
        batch_rows = []

        for i, (intervention_id, content) in enumerate(tqdm(interventions, desc="Tagging")):
            if not content:
                untagged += 1
                continue

            if isinstance(content, memoryview):
                content_str = bytes(content).decode("utf-8")
            elif isinstance(content, bytes):
                content_str = content.decode("utf-8")
            else:
                content_str = str(content)
            slugs = tag_content(content_str)
            if not slugs:
                untagged += 1
                continue

            for slug in slugs:
                tag_id = slug_to_id.get(slug)
                if tag_id:
                    batch_rows.append((intervention_id, tag_id))
                    total_tags += 1

            # Commit per batch
            if len(batch_rows) >= BATCH_SIZE:
                _flush_batch(conn, batch_rows)
                batch_rows = []

        # Flush remaining
        if batch_rows:
            _flush_batch(conn, batch_rows)

        logger.info(
            "Done: %d interventions processed, %d tags assigned, %d untagged",
            len(interventions),
            total_tags,
            untagged,
        )


def _flush_batch(conn, rows: list[tuple[int, int]]) -> None:
    """Insert a batch of (intervention_id, tag_id) rows."""
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO intervention_tags (intervention_id, tag_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            rows,
        )
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Tag interventions with thematic keywords")
    parser.add_argument("--retag-all", action="store_true", help="Clear and retag all interventions")
    args = parser.parse_args()

    tag_interventions(retag_all=args.retag_all)


if __name__ == "__main__":
    main()
