"""Pipeline orchestrator — runs all ingestion scripts in sequence.

Usage:
    python run_all.py                              # Full pipeline (all steps)
    python run_all.py --limit 10                   # Limited debate ingestion
    python run_all.py --skip-actors --skip-organs  # Debates + tags only
    python run_all.py --skip-deputies --skip-debates --retag-all  # Re-tag only
    python run_all.py --skip-debates --skip-tags --skip-deputies  # Actors + organs only
    python run_all.py --senat-zip-path /tmp/cri.zip  # Use pre-downloaded cri.zip

Pipeline order (dependency-safe):
    Step 1: ingest_actors_an.py      (AN deputies from ZIP — must run before organs)
    Step 2: ingest_actors_senat.py   (Senators from API — must run before organs)
    Step 3: ingest_organs_an.py      (AN organs + resolve political_group)
    Step 4: ingest_organs_senat.py   (Senat organs)
    Step 5: ingest_memberships_an.py (AN actor-organ memberships from AMO10 mandats)
    Step 6: ingest_deputies.py       (legacy nosdeputes.fr — backward compat)
    Step 7: ingest_debates.py        (AN CRI debates + interventions)
    Step 8: ingest_debates_senat.py  (Senat CRI debates + interventions from cri.zip)
    Step 9: tag_interventions.py     (FTS tags on interventions)
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
            for table in ["actors", "debates", "interventions", "tags", "intervention_tags", "organs", "actor_organs", "cross_references"]:
                try:
                    cur = conn.execute(f"SELECT count(*) FROM {table}")
                    logger.info("  %-25s %d", table, cur.fetchone()[0])
                except Exception as table_err:
                    logger.warning("  %-25s (error: %s)", table, table_err)
    except Exception as e:
        logger.error("  Could not query DB: %s", e)
    logger.info("  %-25s %.1fs", "Total time", total_time)
    logger.info("  %-25s %d", "Errors", errors)
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Run the full Poliscope ingestion pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Limit debates to ingest")
    parser.add_argument("--start-date", type=str, default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--skip-actors", action="store_true", help="Skip actor ingestion (AN + Senat)")
    parser.add_argument("--skip-organs", action="store_true", help="Skip organ ingestion (AN + Senat)")
    parser.add_argument("--skip-memberships", action="store_true", help="Skip actor-organ membership ingestion (AN)")
    parser.add_argument("--skip-deputies", action="store_true", help="Skip legacy nosdeputes.fr deputy ingestion")
    parser.add_argument("--skip-debates", action="store_true", help="Skip AN debate ingestion")
    parser.add_argument("--skip-senat-debates", action="store_true", help="Skip Senat debate ingestion")
    parser.add_argument("--skip-tags", action="store_true", help="Skip tagging")
    parser.add_argument("--senat-zip-path", type=str, default=None, help="Path to pre-downloaded cri.zip (skips download)")
    parser.add_argument("--retag-all", action="store_true", help="Clear and retag all interventions")
    args = parser.parse_args()

    # Log which steps will run
    logger.info("=" * 60)
    logger.info("PIPELINE PLAN")
    logger.info("=" * 60)
    steps = [
        ("Step 1: ingest_actors_an.py", not args.skip_actors),
        ("Step 2: ingest_actors_senat.py", not args.skip_actors),
        ("Step 3: ingest_organs_an.py", not args.skip_organs),
        ("Step 4: ingest_organs_senat.py", not args.skip_organs),
        ("Step 5: ingest_memberships_an.py", not args.skip_memberships),
        ("Step 6: ingest_deputies.py (legacy)", not args.skip_deputies),
        ("Step 7: ingest_debates.py (AN CRI)", not args.skip_debates),
        ("Step 8: ingest_debates_senat.py (Senat CRI)", not args.skip_senat_debates),
        ("Step 9: tag_interventions.py", not args.skip_tags),
    ]
    for step_name, will_run in steps:
        status = "RUN" if will_run else "SKIP"
        logger.info("  [%s] %s", status, step_name)
    logger.info("=" * 60)

    pipeline_start = time.time()
    errors = 0

    # Step 1: AN actors
    if not args.skip_actors:
        if not run_script("ingest_actors_an.py"):
            errors += 1
    else:
        logger.info("SKIPPED: ingest_actors_an.py")

    # Step 2: Senat actors
    if not args.skip_actors:
        if not run_script("ingest_actors_senat.py"):
            errors += 1
    else:
        logger.info("SKIPPED: ingest_actors_senat.py")

    # Step 3: AN organs (must run after actors to resolve political_group)
    if not args.skip_organs:
        if not run_script("ingest_organs_an.py"):
            errors += 1
    else:
        logger.info("SKIPPED: ingest_organs_an.py")

    # Step 4: Senat organs
    if not args.skip_organs:
        if not run_script("ingest_organs_senat.py"):
            errors += 1
    else:
        logger.info("SKIPPED: ingest_organs_senat.py")

    # Step 5: AN memberships (must run after actors + organs to resolve FKs)
    if not args.skip_memberships:
        if not run_script("ingest_memberships_an.py"):
            errors += 1
    else:
        logger.info("SKIPPED: ingest_memberships_an.py")

    # Step 6: Legacy deputies (nosdeputes.fr — kept for backward compat)
    if not args.skip_deputies:
        if not run_script("ingest_deputies.py"):
            errors += 1
    else:
        logger.info("SKIPPED: ingest_deputies.py (legacy)")

    # Step 7: AN debates
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
        logger.info("SKIPPED: ingest_debates.py (AN CRI)")

    # Step 8: Senat debates
    if not args.skip_senat_debates:
        senat_args = []
        if args.limit is not None:
            senat_args += ["--limit", str(args.limit)]
        if args.senat_zip_path:
            senat_args += ["--senat-zip-path", args.senat_zip_path]
        if not run_script("ingest_debates_senat.py", senat_args):
            errors += 1
    else:
        logger.info("SKIPPED: ingest_debates_senat.py (Senat CRI)")

    # Step 9: Tags
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
