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
import sys
from contextlib import suppress
from pathlib import Path

# Ensure bot/ is on sys.path so `import utils.*` works whether the script is
# run from repo root or from within the bot/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aiohttp
import psycopg
from config.config import Config
from utils.boardgames import fetch_bgg_collection, set_bgg_private

LOG = logging.getLogger("backfill_bgg_private")


def _get_db_conn(config: Config):
    return psycopg.connect(config.database.url)


async def _check_user_and_mark(
    db_conn,
    session: aiohttp.ClientSession,
    user_id,
    bgguser,
    cookie_value: str | None = None,
    dry_run: bool = True,
):
    """Check single user; if 401/403 mark bggprivate

    Returns: tuple (user_id, bgguser, status, marked_bool)
    """
    status = None
    try:
        body, status = await fetch_bgg_collection(
            bgguser, LOG, session, cookie_value=cookie_value, max_attempts=1
        )
    except Exception as e:
        LOG.exception("Unhandled error fetching for %s: %s", bgguser, e)
        return (user_id, bgguser, None, False)

    if status in (401, 403):
        if dry_run:
            LOG.info(
                "[DRY] Would mark user id=%s (%s) private (status=%s)", user_id, bgguser, status
            )
            return (user_id, bgguser, status, False)

        try:
            with suppress(Exception):
                db_conn.rollback()

            if not dry_run:
                await set_bgg_private(db_conn, LOG, user_id)
                LOG.info("Marked user id=%s private via helper", user_id)
            else:
                LOG.info("[DRY] Would mark user id=%s private via helper", user_id)
            return (user_id, bgguser, status, True)
        except Exception as e:
            LOG.exception("Error marking user id=%s private: %s", user_id, e)
            with suppress(Exception):
                db_conn.rollback()
            return (user_id, bgguser, status, False)

    return (user_id, bgguser, status, False)


async def main(dry_run: bool):
    LOG.info("Starting backfill (dry_run=%s)", dry_run)

    config = Config()
    db_conn = _get_db_conn(config)
    cur = db_conn.cursor()

    try:
        cur.execute(
            "SELECT id, bgguser FROM users WHERE bgguser IS NOT NULL AND coalesce(bggprivate, FALSE) = FALSE;"
        )
        users = cur.fetchall()

        LOG.info("Found %d candidates", len(users))

        async with aiohttp.ClientSession() as session:
            tasks = [
                _check_user_and_mark(
                    db_conn,
                    session,
                    uid,
                    bgguser,
                    cookie_value=config.services.bgg_cookie,
                    dry_run=dry_run,
                )
                for uid, bgguser in users
            ]
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
