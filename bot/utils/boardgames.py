import asyncio
import xml.etree.ElementTree as ET

import aiohttp

BASE_URL = "https://api.geekdo.com/xmlapi/"


def safe_convert(value, default=0, data_type=int):
    try:
        return data_type(value)
    except (ValueError, TypeError):
        return default


def parse_bgg_collection(xml_data: str) -> list[dict[str, object]]:
    """Parse BGG collection XML into normalized item dictionaries."""

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return []

    items: list[dict[str, object]] = []
    for item in root.findall("item"):
        status = item.find("status")
        stats = item.find("stats")
        rating = stats.find("rating") if stats is not None else None

        items.append(
            {
                "name": item.findtext("name", default="Unknown"),
                "bggid": item.attrib.get("objectid", "N/A"),
                "avgrating": safe_convert(
                    rating.findtext("average", default="N/A") if rating is not None else "N/A",
                    0.0,
                    float,
                ),
                "own": status.get("own", "0") == "1" if status is not None else False,
                "prevowned": status.get("prevowned", "0") == "1" if status is not None else False,
                "fortrade": status.get("fortrade", "0") == "1" if status is not None else False,
                "want": status.get("want", "0") == "1" if status is not None else False,
                "wanttoplay": status.get("wanttoplay", "0") == "1" if status is not None else False,
                "wanttobuy": status.get("wanttobuy", "0") == "1" if status is not None else False,
                "wishlist": status.get("wishlist", "0") == "1" if status is not None else False,
                "preordered": status.get("preordered", "0") == "1" if status is not None else False,
                "minplayers": safe_convert(stats.get("minplayers") if stats is not None else None, 0),
                "maxplayers": safe_convert(stats.get("maxplayers") if stats is not None else None, 0),
                "minplaytime": safe_convert(stats.get("minplaytime") if stats is not None else None, 0),
                "maxplaytime": safe_convert(stats.get("maxplaytime") if stats is not None else None, 0),
                "numplays": safe_convert(item.findtext("numplays", default="0"), 0),
            }
        )

    return items


async def fetch_bgg_collection(
    username,
    logger,
    session: aiohttp.ClientSession,
    cookie_value: str | None = None,
    max_attempts: int = 3,
    backoff: float = 2.0,
):
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

    last_status = None

    for attempt in range(1, max_attempts + 1):
        try:
            headers = {"User-Agent": "DarkBot (https://github.com/benjamind10/darkbot)"}

            if cookie_value:
                headers["Cookie"] = cookie_value

            async with session.get(url, headers=headers) as response:
                status = response.status

                if status == 200:
                    logger.info("Successfully fetched collection for user: %s", username)
                    return (await response.text(), 200)

                if status == 202:
                    last_status = status
                    logger.info(
                        "Collection for %s is queued (202). Attempt %d/%d — retrying after 5s",
                        username,
                        attempt,
                        max_attempts,
                    )
                    await asyncio.sleep(5)
                    continue

                if status == 429:
                    last_status = status
                    ra = response.headers.get("Retry-After")
                    delay = float(ra) if ra and ra.isnumeric() else backoff**attempt
                    logger.warning(
                        "Rate limited when fetching %s; attempt %d/%d. Retry after %s sec",
                        username,
                        attempt,
                        max_attempts,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                if status in (401, 403):
                    short_body = (await response.text())[:1000]
                    logger.error(
                        "Authorization error fetching BGG for %s: %s %s -- body(first1000): %s",
                        username,
                        status,
                        response.reason,
                        short_body,
                    )
                    logger.warning(
                        "Hint: this usually means the user's collection is private or the API requires a logged-in session.\n"
                        "To fetch private collections, set BGG_COOKIE or BGG_AUTH_COOKIE in your environment with a valid session cookie (e.g. 'bb=...; other=...').\n"
                        "If you don't need private collections, ask the user to make their collection public or skip private accounts.",
                    )
                    return (None, status)

                if 500 <= status < 600:
                    last_status = status
                    delay = backoff**attempt
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
            logger.exception(
                "ClientResponseError while fetching BGG for %s (attempt %d/%d): %s",
                username,
                attempt,
                max_attempts,
                cre,
            )
            if getattr(cre, "status", None) in (401, 403):
                return (None, cre.status)
            await asyncio.sleep(backoff**attempt)

        except aiohttp.ClientError as e:
            logger.exception(
                "ClientError fetching BGG for %s (attempt %d/%d): %s",
                username,
                attempt,
                max_attempts,
                e,
            )
            await asyncio.sleep(backoff**attempt)

        except asyncio.CancelledError:
            raise

        except Exception as e:
            logger.exception(
                "Unexpected error fetching BGG for %s (attempt %d/%d): %s",
                username,
                attempt,
                max_attempts,
                e,
            )
            await asyncio.sleep(backoff**attempt)

    logger.error(
        "Failed to retrieve BGG collection after %d attempts for user %s",
        max_attempts,
        username,
    )
    return (None, last_status)


async def upsert_boardgame(db_pool, logger, game_data):
    try:
        async with db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
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
        logger.info(
            f"Upsert successful for game {game_data['name']} (BGG ID: {game_data['bggid']})"
        )
    except Exception as e:
        logger.exception(f"Exception occurred while upserting game {game_data['name']}: {e}")
        raise


async def set_bgg_private(db_pool, logger, user_id: int, is_private: bool = True) -> None:
    try:
        if hasattr(db_pool, "connection"):
            async with db_pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT set_bgg_private(%s, %s);", (user_id, is_private))
        else:
            with db_pool.cursor() as cursor:
                cursor.execute("SELECT set_bgg_private(%s, %s);", (user_id, is_private))
            if hasattr(db_pool, "commit"):
                db_pool.commit()
        logger.info("Marked user id=%s bggprivate=%s via SQL helper", user_id, is_private)
    except Exception as e:
        logger.exception(f"Exception occurred while marking user {user_id} private: {e}")
        raise


async def process_bgg_users(
    db_pool, session: aiohttp.ClientSession, logger, cookie_value: str | None = None
):
    try:
        async with db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                logger.debug("Fetching users.")
                await cursor.execute("SELECT id, bgguser FROM get_all_bggusers();")
                users = await cursor.fetchall()
                logger.debug(f"Fetched {len(users)} users.")

        logger.info(f"Processing {len(users)} users' BGG collections.")
        for user_id, bgguser in users:
            try:
                xml_data, status = await fetch_bgg_collection(
                    bgguser, logger, session, cookie_value=cookie_value
                )

                if status in (401, 403):
                    try:
                        logger.info("Marking user id=%s as having a private BGG account", user_id)
                        await set_bgg_private(db_pool, logger, user_id)
                    except Exception as mark_exc:
                        logger.warning(
                            "Could not mark user %s as private via helper (maybe migration missing): %s",
                            user_id,
                            mark_exc,
                        )
                    logger.warning(
                        "No data returned for user %s — skipping (auth %s)", bgguser, status
                    )
                    continue

                if not xml_data:
                    logger.warning("No data returned for user %s — skipping", bgguser)
                    continue

                games = parse_bgg_collection(xml_data)
                if not games:
                    logger.warning(
                        "No parsable collection items for user %s; first 500 chars: %s",
                        bgguser,
                        (xml_data or "")[:500],
                    )
                    continue

                for parsed_item in games:
                    game_data = {"userid": user_id, **parsed_item}

                    try:
                        await upsert_boardgame(db_pool, logger, game_data)
                    except Exception:
                        logger.warning(
                            "Upsert failed for user %s game %s — continuing",
                            bgguser,
                            game_data.get("name"),
                        )

            except Exception as e:
                logger.exception(
                    "Critical error processing user %s (id=%s): %s",
                    bgguser,
                    user_id,
                    e,
                )
                continue
    except Exception as e:
        logger.exception(f"Critical error processing users: {e}")
