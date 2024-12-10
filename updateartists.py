from datetime import datetime, timezone
import psycopg2
import requests
from config.logging import logger
from config.config import DATABASE_URL, TICKETMASTER_API_KEY

now = datetime.now(timezone.utc)

def find_artist_id(keyword):
    url = f"https://app.ticketmaster.com/discovery/v2/attractions?apikey={TICKETMASTER_API_KEY}&keyword={keyword}&locale=*"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    return data["_embedded"]["attractions"][0]["id"]

def mark_artists_notable(artist_id):
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE Artists
                SET notable = TRUE
                WHERE artistID = %s
                """,
                (artist_id,)
            )
        conn.commit()
        logger.info(f"Marked artist {artist_id} as notable.")
    finally:
        conn.close()

if __name__ == "__main__":
    keyword = "Gracie Abrams"
    artist_id = find_artist_id(keyword)
    mark_artists_notable(artist_id)