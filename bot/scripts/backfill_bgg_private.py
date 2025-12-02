#!/usr/bin/env python3
"""Backfill script: mark users whose BGG collection requires auth as private.

This script will:
 - Iterate all users that have a BGG username and are not already marked private
 - Call fetch_bgg_collection once and if the returned status is 401/403 mark the
   user as private (bggprivate = TRUE and update datemodified)

Usage:
  # dry-run (no DB updates)
  ./backfill_bgg_private.py --dry-run

  # live run (will update DB)
  ./backfill_bgg_private.py

This runs inside the bot package so run from repo root::
  cd bot
  ../venv/bin/python scripts/backfill_bgg_private.py

Be careful: this will update your database. It's recommended to run with --dry-run
first to inspect what would be marked.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Ensure bot/ is on sys.path so `import utils.*` works whether the script is
# run from repo root or from within the bot/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

# use package imports
from utils.boardgames import fetch_bgg_collection, BASE_URL

import psycopg2

LOG = logging.getLogger("backfill_bgg_private")


def _get_db_conn_from_env():
    dbname = os.getenv("DB_NAME") or os.getenv("DBNAME")
    user = os.getenv("DB_USER") or os.getenv("DBUSER")
    password = os.getenv("DB_PASS") or os.getenv("DBPASS")
    host = os.getenv("DB_HOST") or os.getenv("DBHOST")
    port = os.getenv("DB_PORT") or os.getenv("DBPORT")

    return psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)


async def _check_user_and_mark(db_conn, user_id, bgguser, dry_run: bool = True):
    """Check single user; if 401/403 mark bggprivate

    Returns: tuple (user_id, bgguser, status, marked_bool)
    """
    status = None
    try:
        body, status = await fetch_bgg_collection(bgguser, LOG, max_attempts=1)
    except Exception as e:
        LOG.exception("Unhandled error fetching for %s: %s", bgguser, e)
        return (user_id, bgguser, None, False)

    if status in (401, 403):
        if dry_run:
            LOG.info("[DRY] Would mark user id=%s (%s) private (status=%s)", user_id, bgguser, status)
            return (user_id, bgguser, status, False)

        cur = db_conn.cursor()
        try:
            # defensive rollback to clear any aborted transactions
            try:
                db_conn.rollback()
            except Exception:
                LOG.debug("rollback failed (ignored)")

            cur.execute(
                "UPDATE users SET bggprivate = TRUE, datemodified = CURRENT_TIMESTAMP WHERE id = %s RETURNING datemodified;",
                (user_id,),
            )
            updated = cur.fetchone()
            db_conn.commit()
            LOG.info("Marked user id=%s private; datemodified=%s", user_id, updated[0] if updated else None)
            return (user_id, bgguser, status, True)
        except Exception as e:
            LOG.exception("Error marking user id=%s private: %s", user_id, e)
            try:
                db_conn.rollback()
            except Exception:
                pass
            return (user_id, bgguser, status, False)
        finally:
            cur.close()

    # Not a 401/403 — nothing to do
    return (user_id, bgguser, status, False)


async def main(dry_run: bool):
    LOG.info("Starting backfill (dry_run=%s)", dry_run)

    db_conn = _get_db_conn_from_env()
    cur = db_conn.cursor()

    try:
        # Fetch users who have a bgguser and are not marked private
        cur.execute("SELECT id, bgguser FROM users WHERE bgguser IS NOT NULL AND coalesce(bggprivate, FALSE) = FALSE;")
        users = cur.fetchall()

        LOG.info("Found %d candidates", len(users))

        tasks = []
        for uid, bgguser in users:
            tasks.append(_check_user_and_mark(db_conn, uid, bgguser, dry_run=dry_run))

        results = await asyncio.gather(*tasks)

        marked = [r for r in results if r[3]]
        LOG.info("Backfill complete — total candidates=%d marked=%d", len(users), len(marked))

    finally:
        cur.close()
        db_conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Don't update DB; just report")
    parser.add_argument("--debug", action="store_true", help="Enable debug log")

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    asyncio.run(main(args.dry_run))
