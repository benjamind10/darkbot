import asyncio
import aiohttp
import os
import xml.etree.ElementTree as ET

BASE_URL = "https://api.geekdo.com/xmlapi/"


def safe_convert(value, default=0, data_type=int):
    try:
        return data_type(value)
    except (ValueError, TypeError):
        return default


async def fetch_bgg_collection(username, logger, max_attempts: int = 3, backoff: float = 2.0):
    """Fetch a user's BGG collection with retries for transient errors and
    improved logging for diagnostics.

    Behavior:
    - 200 -> return body
    - 202 -> server is processing; retry with fixed delay
    - 429 -> respect Retry-After header if present, otherwise backoff
    - 401/403 -> authorization error: log detailed info and return None (no retry)
    - 5xx -> retry with exponential backoff
    - other statuses -> log and return None
    """

    url = f"{BASE_URL}collection/{username}?stats=1"
    logger.info("Attempting to fetch BGG collection for user: %s", username)

    # Support optional authentication via environment variable.
    cookie_value = os.getenv("BGG_AUTH_COOKIE") or os.getenv("BGG_COOKIE")

    async with aiohttp.ClientSession() as session:
        for attempt in range(1, max_attempts + 1):
            try:
                headers = {
                    # BGG's API is public but some endpoints can throttle or block
                    # unknown / empty user-agents. Set a clear user agent so the
                    # BGG servers can contact/identify the client if needed.
                    "User-Agent": "DarkBot (https://github.com/benjamind10/darkbot)"
                }

                if cookie_value:
                    headers["Cookie"] = cookie_value

                async with session.get(url, headers=headers) as response:
                    status = response.status

                    # Helpful minimal context for logs
                    context = {
                        "username": username,
                        "url": url,
                        "status": status,
                        "attempt": attempt,
                    }

                    if status == 200:
                        logger.info("Successfully fetched collection for user: %s", username)
                        return (await response.text(), 200)

                    # Server says the collection is being prepared — wait and retry
                    if status == 202:
                        logger.info(
                            "Collection for %s is queued (202). Attempt %d/%d — retrying after 5s",
                            username,
                            attempt,
                            max_attempts,
                        )
                        await asyncio.sleep(5)
                        continue

                    # Rate limited — look for Retry-After header
                    if status == 429:
                        ra = response.headers.get("Retry-After")
                        delay = float(ra) if ra and ra.isnumeric() else backoff ** attempt
                        logger.warning(
                            "Rate limited when fetching %s; attempt %d/%d. Retry after %s sec",
                            username,
                            attempt,
                            max_attempts,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue

                    # Authorization errors — do not retry, but log detailed info
                    if status in (401, 403):
                        short_body = (await response.text())[:1000]
                        logger.error(
                            "Authorization error fetching BGG for %s: %s %s -- body(first1000): %s",
                            username,
                            status,
                            response.reason,
                            short_body,
                        )
                        # Provide helpful hint for operators
                        logger.warning(
                            "Hint: this usually means the user's collection is private or the API requires a logged-in session.\n"
                            "To fetch private collections, set BGG_COOKIE or BGG_AUTH_COOKIE in your environment with a valid session cookie (e.g. 'bb=...; other=...').\n"
                            "If you don't need private collections, ask the user to make their collection public or skip private accounts.",
                        )
                        return (None, status)

                    # Server errors — retry with exponential backoff
                    if 500 <= status < 600:
                        delay = backoff ** attempt
                        logger.warning(
                            "Server error %s for %s; attempt %d/%d. Retrying after %.1f sec",
                            status,
                            username,
                            attempt,
                            max_attempts,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue

                    # Non-handled status — log and stop for this user
                    short_body = (await response.text())[:1000]
                    logger.warning(
                        "Unexpected status fetching %s: %s %s — body(first1000): %s",
                        username,
                        status,
                        response.reason,
                        short_body,
                    )
                    return (None, status)

            except aiohttp.ClientResponseError as cre:
                # aiohttp raises this for certain response errors; log context and continue or break
                logger.exception(
                    "ClientResponseError while fetching BGG for %s (attempt %d/%d): %s",
                    username,
                    attempt,
                    max_attempts,
                    cre,
                )
                # For auth errors the status is available; don't retry
                if getattr(cre, "status", None) in (401, 403):
                    return None
                # otherwise back off and retry
                await asyncio.sleep(backoff ** attempt)

            except aiohttp.ClientError as e:
                # Transport-level errors
                logger.exception(
                    "ClientError fetching BGG for %s (attempt %d/%d): %s",
                    username,
                    attempt,
                    max_attempts,
                    e,
                )
                await asyncio.sleep(backoff ** attempt)

            except asyncio.CancelledError:
                # propagate cancellation
                raise

            except Exception as e:
                logger.exception(
                    "Unexpected error fetching BGG for %s (attempt %d/%d): %s",
                    username,
                    attempt,
                    max_attempts,
                    e,
                )
                await asyncio.sleep(backoff ** attempt)

        logger.error(
            "Failed to retrieve BGG collection after %d attempts for user %s",
            max_attempts,
            username,
        )
        return (None, None)


async def upsert_boardgame(db, logger, game_data):
    try:
        cursor = db.cursor()
        try:
            cursor.execute(
                """
                SELECT upsert_boardgame(
                    CAST(%s AS INTEGER),
                    CAST(%s AS VARCHAR),
                    CAST(%s AS INTEGER),
                    CAST(%s AS DOUBLE PRECISION),
                    CAST(%s AS BOOLEAN),
                    CAST(%s AS BOOLEAN),
                    CAST(%s AS BOOLEAN),
                    CAST(%s AS BOOLEAN),
                    CAST(%s AS BOOLEAN),
                    CAST(%s AS BOOLEAN),
                    CAST(%s AS BOOLEAN),
                    CAST(%s AS BOOLEAN),
                    CAST(%s AS INTEGER),
                    CAST(%s AS INTEGER),
                    CAST(%s AS INTEGER),
                    CAST(%s AS INTEGER)
                );
                """,
                (
                    game_data["userid"],
                    game_data["name"],
                    game_data["bggid"],
                    game_data["avgrating"],
                    game_data["own"],
                    game_data["prevowned"],
                    game_data["fortrade"],
                    game_data["want"],
                    game_data["wanttoplay"],
                    game_data["wanttobuy"],
                    game_data["wishlist"],
                    game_data["preordered"],
                    game_data["minplayers"],
                    game_data["maxplayers"],
                    game_data["minplaytime"],
                    game_data["numplays"],
                ),
            )
            db.commit()
            logger.info(
                f"Upsert successful for game {game_data['name']} (BGG ID: {game_data['bggid']})"
            )
        finally:
            cursor.close()
    except Exception as e:
        logger.exception(
            f"Exception occurred while upserting game {game_data['name']}: {e}"
        )
        raise


async def process_bgg_users(db, logger):
    try:
        cursor = db.cursor()
        try:
            logger.debug("Fetching users.")
            cursor.execute("SELECT id, bgguser FROM users WHERE bgguser IS NOT NULL;")
            users = cursor.fetchall()
            logger.debug(f"Fetched {len(users)} users.")
        finally:
            cursor.close()

        logger.info(f"Processing {len(users)} users' BGG collections.")
        for user_id, bgguser in users:
            try:
                xml_data, status = await fetch_bgg_collection(bgguser, logger)

                # If we hit an authorization error mark the DB user as private
                if status in (401, 403):
                    try:
                        logger.info(
                            "Marking user id=%s as having a private BGG account", user_id
                        )

                        # It's possible the connection is already in an error state
                        # (e.g. earlier exception left the transaction aborted). Do a
                        # defensive rollback before trying to write so the UPDATE can
                        # execute cleanly. If rollback fails we log a debug note and
                        # still attempt the update.
                        try:
                            db.rollback()
                        except Exception as rb_exc:  # pragma: no cover - defensive
                            logger.debug(
                                "Rollback before marking private failed (ignoring): %s",
                                rb_exc,
                            )

                        cur = db.cursor()
                        try:
                            cur.execute(
                                "UPDATE users SET bggprivate = TRUE, datemodified = CURRENT_TIMESTAMP WHERE id = %s RETURNING datemodified;",
                                (user_id,),
                            )
                            updated = cur.fetchone()
                            db.commit()
                            if updated:
                                logger.info("Marked user id=%s private; datemodified=%s", user_id, updated[0])
                        finally:
                            cur.close()
                    except Exception as mark_exc:  # pragma: no cover - best-effort marking
                        logger.warning(
                            "Could not mark user %s as private in DB (maybe migration missing): %s",
                            user_id,
                            mark_exc,
                        )
                    logger.warning("No data returned for user %s — skipping (auth %s)", bgguser, status)
                    continue

                if not xml_data:
                    logger.warning("No data returned for user %s — skipping", bgguser)
                    continue

                try:
                    root = ET.fromstring(xml_data)
                except ET.ParseError as pe:
                    logger.exception(
                        "Failed to parse XML for %s — first 500 chars: %s",
                        bgguser,
                        (xml_data or '')[:500],
                    )
                    continue

                for item in root.findall("item"):
                    status = item.find("status")
                    game_data = {
                        "userid": user_id,
                        "name": (
                            item.find("name").text
                            if item.find("name") is not None
                            else "Unknown"
                        ),
                        "bggid": safe_convert(item.get("objectid"), 0),
                        "avgrating": safe_convert(
                            item.find("stats/rating/average").get("value"), 0.0, float
                        ),
                        "own": status.get("own", "0") == "1",
                        "prevowned": status.get("prevowned", "0") == "1",
                        "fortrade": status.get("fortrade", "0") == "1",
                        "want": status.get("want", "0") == "1",
                        "wanttoplay": status.get("wanttoplay", "0") == "1",
                        "wanttobuy": status.get("wanttobuy", "0") == "1",
                        "wishlist": status.get("wishlist", "0") == "1",
                        "preordered": status.get("preordered", "0") == "1",
                        "minplayers": safe_convert(
                            item.find("stats").get("minplayers"), 0
                        ),
                        "maxplayers": safe_convert(
                            item.find("stats").get("maxplayers"), 0
                        ),
                        "minplaytime": safe_convert(
                            item.find("stats").get("minplaytime"), 0
                        ),
                        "numplays": safe_convert(item.find("numplays").text, 0),
                    }

                    try:
                        await upsert_boardgame(db, logger, game_data)
                    except Exception:
                        # upsert_boardgame logs the exception; move on to the next item
                        logger.warning(
                            "Upsert failed for user %s game %s — continuing",
                            bgguser,
                            game_data.get("name"),
                        )

            except Exception as e:
                # Catch per-user exceptions so one bad account doesn't stop the entire run
                logger.exception(
                    "Critical error processing user %s (id=%s): %s",
                    bgguser,
                    user_id,
                    e,
                )
                continue
    except Exception as e:
        logger.exception(f"Critical error processing users: {e}")
