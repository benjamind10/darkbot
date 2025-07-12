import asyncio
import aiohttp
import xml.etree.ElementTree as ET

BASE_URL = "https://api.geekdo.com/xmlapi/"


def safe_convert(value, default=0, data_type=int):
    try:
        return data_type(value)
    except (ValueError, TypeError):
        return default


async def fetch_bgg_collection(username, logger):
    url = f"{BASE_URL}collection/{username}?stats=1"
    logger.info(f"Attempting to fetch BGG collection for user: {username}")
    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            async with session.get(url) as response:
                if response.status == 200:
                    logger.info(f"Successfully fetched collection for user: {username}")
                    return await response.text()
                elif response.status == 202:
                    logger.info(
                        f"Received 202 response for user: {username}, attempt {attempt+1}. Retrying after 5 seconds..."
                    )
                    await asyncio.sleep(5)
                else:
                    logger.warning(
                        f"Failed to fetch collection for user: {username} with status: {response.status}"
                    )
                    response.raise_for_status()
        logger.error(f"Failed to retrieve data after 3 attempts for user: {username}")
        return None


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
            xml_data = await fetch_bgg_collection(bgguser, logger)
            if xml_data:
                root = ET.fromstring(xml_data)
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

                    await upsert_boardgame(db, logger, game_data)
            else:
                logger.warning(f"No data to process for user {bgguser}")
    except Exception as e:
        logger.exception(f"Critical error processing users: {e}")
