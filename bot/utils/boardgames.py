import asyncio
import html
import re
import xml.etree.ElementTree as ET

import aiohttp

BASE_URL = "https://boardgamegeek.com/xmlapi/"
API2_BASE_URL = "https://boardgamegeek.com/xmlapi2/"
HTML_BASE_URL = "https://boardgamegeek.com/"
BGG_USER_AGENT = "DarkBot (https://github.com/benjamind10/darkbot)"
BGG_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}
SET_BGG_PRIVATE_SQL = """
UPDATE users
SET bggprivate = %s::boolean, datemodified = CURRENT_TIMESTAMP
WHERE id = %s::integer;
"""


def has_bgg_cookie(cookie_value: str | None) -> bool:
    return bool(cookie_value and cookie_value.strip())


def safe_convert(value, default=0, data_type=int):
    try:
        return data_type(value)
    except (ValueError, TypeError):
        return default


def parse_bgg_search(xml_data: str) -> list[dict[str, str]]:
    """Parse BGG XML API2 search results into normalized dictionaries."""

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return []

    results: list[dict[str, str]] = []
    for item in root.findall("item"):
        name = next(
            (name_el.attrib.get("value") for name_el in item.findall("name") if name_el.attrib.get("type") == "primary"),
            None,
        )
        if not name:
            name_el = item.find("name")
            name = name_el.attrib.get("value") if name_el is not None else "Unknown"

        results.append(
            {
                "bggid": item.attrib.get("id", "N/A"),
                "name": name,
                "yearpublished": item.find("yearpublished").attrib.get("value", "N/A")
                if item.find("yearpublished") is not None
                else "N/A",
            }
        )

    return results


def parse_bgg_search_html(html_data: str) -> list[dict[str, str]]:
    """Parse BGG HTML search results into normalized dictionaries."""

    results: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    pattern = re.compile(
        r"<a\s+[^>]*href=[\"']/boardgame/(?P<id>\d+)/[^\"']*[\"'][^>]*class=[\"']primary[\"'][^>]*>"
        r"(?P<name>.*?)</a>\s*<span\s+class=[\"']smallerfont dull[\"']>\((?P<year>[^)]*)\)</span>",
        re.IGNORECASE | re.DOTALL,
    )

    for match in pattern.finditer(html_data):
        bggid = match.group("id")
        if bggid in seen_ids:
            continue

        name = re.sub(r"<[^>]+>", "", match.group("name"))
        results.append(
            {
                "bggid": bggid,
                "name": html.unescape(name).strip() or "Unknown",
                "yearpublished": html.unescape(match.group("year")).strip() or "N/A",
            }
        )
        seen_ids.add(bggid)

    return results


def parse_bgg_thing(xml_data: str) -> dict[str, object] | None:
    """Parse BGG XML API2 thing response into embed-friendly fields."""

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return None

    item = root.find("item")
    if item is None:
        return None

    name = next(
        (name_el.attrib.get("value") for name_el in item.findall("name") if name_el.attrib.get("type") == "primary"),
        None,
    )
    if not name:
        name = item.find("name").attrib.get("value", "Unknown") if item.find("name") is not None else "Unknown"

    stats = item.find("statistics/ratings")
    poll = item.find("poll[@name='suggested_numplayers']")
    best_count = "N/A"
    max_votes = -1
    if poll is not None:
        for results in poll.findall("results"):
            best = results.find("result[@value='Best']")
            if best is None:
                continue
            votes = safe_convert(best.attrib.get("numvotes"), 0)
            if votes > max_votes:
                max_votes = votes
                best_count = results.attrib.get("numplayers", "N/A")

    avg_rating = "N/A"
    users_rated = "N/A"
    if stats is not None:
        average_el = stats.find("average")
        users_rated_el = stats.find("usersrated")
        avg_rating = average_el.attrib.get("value", "N/A") if average_el is not None else "N/A"
        users_rated = users_rated_el.attrib.get("value", "N/A") if users_rated_el is not None else "N/A"
        if avg_rating != "N/A":
            avg_rating = f"{float(avg_rating):.2f}"

    return {
        "bggid": item.attrib.get("id", "N/A"),
        "name": name,
        "yearpublished": item.find("yearpublished").attrib.get("value", "N/A") if item.find("yearpublished") is not None else "N/A",
        "minage": item.find("minage").attrib.get("value", "N/A") if item.find("minage") is not None else "N/A",
        "users_rated": users_rated,
        "avg_rating": avg_rating,
        "best_count": best_count,
    }


def parse_bgg_collection(xml_data: str) -> list[dict[str, object]]:
    """Parse BGG collection XML into normalized item dictionaries."""

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return []

    items: list[dict[str, object]] = []
    for item in root.findall("item"):
        name_element = item.find("name")
        status = item.find("status")
        stats = item.find("stats")
        rating = stats.find("rating") if stats is not None else None
        name = "Unknown"
        if name_element is not None:
            name = name_element.attrib.get("value") or name_element.text or name

        items.append(
            {
                "name": name,
                "bggid": item.attrib.get("objectid", "N/A"),
                "avgrating": safe_convert(
                    rating.attrib.get("value", "N/A") if rating is not None else "N/A",
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

    url = f"{API2_BASE_URL}collection"
    logger.info("Attempting to fetch BGG collection for user: %s", username)

    last_status = None

    for attempt in range(1, max_attempts + 1):
        try:
            headers = {"User-Agent": BGG_USER_AGENT}

            params = {"username": username, "stats": 1, "subtype": "boardgame"}

            if cookie_value:
                headers["Cookie"] = cookie_value
                params["showprivate"] = 1

            async with session.get(url, headers=headers, params=params) as response:
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
                    if has_bgg_cookie(cookie_value):
                        logger.warning(
                            "Hint: BGG returned %s for %s even though a cookie was configured. The cookie may be invalid, expired, or not authorized for this account.",
                            status,
                            username,
                        )
                    else:
                        logger.warning(
                            "Hint: this usually means the user's collection is private or the API requires a logged-in session.\n"
                            "To fetch private collections, set BGG_AUTH_COOKIE in your environment with a valid session cookie (e.g. 'bb=...; other=...').\n"
                            "BGG_COOKIE is still accepted as a legacy alias.\n"
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
                    await cursor.execute(SET_BGG_PRIVATE_SQL, (is_private, user_id))
        else:
            with db_pool.cursor() as cursor:
                cursor.execute(SET_BGG_PRIVATE_SQL, (is_private, user_id))
            if hasattr(db_pool, "commit"):
                db_pool.commit()
        logger.info("Marked user id=%s bggprivate=%s", user_id, is_private)
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
                    if has_bgg_cookie(cookie_value):
                        logger.info(
                            "User %s (%s) returned %s from BGG with a configured cookie; not marking private.",
                            user_id,
                            bgguser,
                            status,
                        )
                    else:
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
                            "User %s (%s) returned %s from BGG without a cookie — marking as private.",
                            user_id,
                            bgguser,
                            status,
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
