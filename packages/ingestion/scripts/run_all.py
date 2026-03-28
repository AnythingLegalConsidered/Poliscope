"""Pipeline orchestrator — runs all ingestion scripts in sequence.

Usage:
    python run_all.py                              # Full pipeline
    python run_all.py --limit 10                   # Limited debate ingestion
    python run_all.py --skip-deputies --skip-debates --retag-all  # Re-tag only
"""

import argparse
import logging
import subprocess
import sys
import time

from db import get_connection

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SCRIPTS_DIR = __file__.replace("\\", "/").rsplit("/", 1)[0]


def run_script(name: str, args: list[str] | None = None) -> bool:
    """Run a Python script as subprocess. Returns True on success."""
    script_path = f"{SCRIPTS_DIR}/{name}"
    cmd = [sys.executable, script_path] + (args or [])
    logger.info("=" * 60)
    logger.info("RUNNING: %s %s", name, " ".join(args or []))
    logger.info("=" * 60)
    start = time.time()
    try:
        subprocess.run(cmd, check=True)
        elapsed = time.time() - start
        logger.info("COMPLETED: %s (%.1fs)", name, elapsed)
        return True
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start
        logger.error("FAILED: %s (exit code %d, %.1fs)", name, e.returncode, elapsed)
        return False


def print_summary(total_time: float, errors: int) -> None:
    """Query DB counts and print final summary."""
    logger.info("=" * 60)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 60)
    try:
        with get_connection() as conn:
            for table in ["deputies", "debates", "interventions", "tags", "intervention_tags"]:
                cur = conn.execute(f"SELECT count(*) FROM {table}")
                logger.info("  %-20s %d", table, cur.fetchone()[0])
    except Exception as e:
        logger.error("  Could not query DB: %s", e)
    logger.info("  %-20s %.1fs", "Total time", total_time)
    logger.info("  %-20s %d", "Errors", errors)
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Run the full Poliscope ingestion pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Limit debates to ingest")
    parser.add_argument("--start-date", type=str, default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--skip-deputies", action="store_true", help="Skip deputy ingestion")
    parser.add_argument("--skip-debates", action="store_true", help="Skip debate ingestion")
    parser.add_argument("--skip-tags", action="store_true", help="Skip tagging")
    parser.add_argument("--retag-all", action="store_true", help="Clear and retag all interventions")
    args = parser.parse_args()

    pipeline_start = time.time()
    errors = 0

    # Step 1: Deputies
    if not args.skip_deputies:
        if not run_script("ingest_deputies.py"):
            errors += 1
    else:
        logger.info("SKIPPED: ingest_deputies.py")

    # Step 2: Debates
    if not args.skip_debates:
        debate_args = []
        if args.limit is not None:
            debate_args += ["--limit", str(args.limit)]
        if args.start_date:
            debate_args += ["--start-date", args.start_date]
        if args.end_date:
            debate_args += ["--end-date", args.end_date]
        if not run_script("ingest_debates.py", debate_args):
            errors += 1
    else:
        logger.info("SKIPPED: ingest_debates.py")

    # Step 3: Tags
    if not args.skip_tags:
        tag_args = []
        if args.retag_all:
            tag_args.append("--retag-all")
        if not run_script("tag_interventions.py", tag_args):
            errors += 1
    else:
        logger.info("SKIPPED: tag_interventions.py")

    # Summary
    total_time = time.time() - pipeline_start
    print_summary(total_time, errors)


if __name__ == "__main__":
    main()
