import asyncio
import aiohttp
import psycopg2
import xml.etree.ElementTree as ET

from db import get_connection
from logging_files.boardgames_util_logging import logger

BASE_URL = "https://api.geekdo.com/xmlapi/"


async def fetch_bgg_collection(username):
    url = f"{BASE_URL}collection/{username}?own=1&stats=1"
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


async def upsert_boardgame(conn, game_data):
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
            SELECT upsert_boardgame(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
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
                    game_data["maxplaytime"],
                ),
            )
            conn.commit()
            logger.info(
                f"Upsert successful for game {game_data['name']} (BGG ID: {game_data['bggid']})"
            )
    except Exception as e:
        logger.exception(
            f"Exception occurred while upserting game {game_data['name']}: {e}"
        )
        raise


async def process_bgg_users():
    conn = get_connection()
    logger.info(conn)
    try:
        with conn.cursor() as cursor:
            logger.debug("Fetching users.")
            cursor.execute("SELECT id, bgguser FROM users WHERE bgguser IS NOT NULL;")
            users = cursor.fetchall()
            logger.debug(f"Fetched {len(users)} users.")

        logger.info(f"Processing {len(users)} users' BGG collections.")
        for user_id, bgguser in users:
            xml_data = await fetch_bgg_collection(bgguser)
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
                        "bggid": item.get(
                            "objectid", "Unknown"
                        ),  # Use get with default on attributes directly from item
                        "avgrating": (
                            item.find("stats/rating/average").get("value", "N/A")
                            if item.find("stats/rating/average") is not None
                            else "N/A"
                        ),
                        "own": item.find("status").get("own", "0") == "1",
                        "prevowned": item.find("status").get("prevowned", "0") == "1",
                        "fortrade": item.find("status").get("fortrade", "0") == "1",
                        "want": item.find("status").get("want", "0") == "1",
                        "wanttoplay": item.find("status").get("wanttoplay", "0") == "1",
                        "wanttobuy": item.find("status").get("wanttobuy", "0") == "1",
                        "wishlist": item.find("status").get("wishlist", "0") == "1",
                        "preordered": item.find("status").get("preordered", "0") == "1",
                        "minplayers": (
                            item.find("stats").get("minplayers", "N/A")
                            if item.find("stats") is not None
                            else "N/A"
                        ),
                        "maxplayers": (
                            item.find("stats").get("maxplayers", "N/A")
                            if item.find("stats") is not None
                            else "N/A"
                        ),
                        "minplaytime": (
                            item.find("stats").get("minplaytime", "N/A")
                            if item.find("stats") is not None
                            else "N/A"
                        ),
                        "maxplaytime": (
                            item.find("stats").get("maxplaytime", "N/A")
                            if item.find("stats") is not None
                            else "N/A"
                        ),
                        "numplays": (
                            item.find("numplays").text
                            if item.find("numplays") is not None
                            else "0"
                        ),
                    }

                    game_data = {
                        "userid": int(game_data["userid"]),
                        "name": game_data["name"],
                        "bggid": int(game_data["bggid"]),
                        "avgrating": float(game_data["avgrating"]),
                        "own": game_data["own"],
                        "prevowned": game_data["prevowned"],
                        "fortrade": game_data["fortrade"],
                        "want": game_data["want"],
                        "wanttoplay": game_data["wanttoplay"],
                        "wanttobuy": game_data["wanttobuy"],
                        "wishlist": game_data["wishlist"],
                        "preordered": game_data["preordered"],
                        "minplayers": int(game_data["minplayers"]),
                        "maxplayers": int(game_data["maxplayers"]),
                        "minplaytime": int(game_data["minplaytime"]),
                        "maxplaytime": int(game_data["maxplaytime"]),
                        "numplays": int(game_data["numplays"]),
                    }

                    logger.info(game_data)
                    await upsert_boardgame(conn, game_data)
            else:
                logger.warning(f"No data to process for user {bgguser}")
    except Exception as e:
        logger.exception(f"Critical error processing users: {e}")
    finally:
        conn.close()
        logger.info("Database connection closed.")


__all__ = ["process_bgg_users"]
