"""
DDS Daily Agent — runs every day at a configured time and refreshes the cache.
Start with: python agent.py
"""
import schedule
import time
import logging
from datetime import datetime
from data_fetcher import fetch_and_process

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AGENT] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

RUN_AT = "11:00"  # Change this to your preferred daily refresh time (24h format)

def daily_refresh():
    logging.info("Starting daily DDS sheet refresh...")
    try:
        data = fetch_and_process()
        logging.info(
            f"Done. {data['total_skus']} SKUs | "
            f"{data['total_completed']} completed | "
            f"{data['total_pending']} pending | "
            f"{data['total_not_started']} not started"
        )
    except Exception as e:
        logging.error(f"Refresh failed: {e}")

if __name__ == "__main__":
    logging.info(f"DDS Agent started. Will refresh daily at {RUN_AT}.")
    # Run once immediately on start
    daily_refresh()
    # Then schedule daily
    schedule.every().day.at(RUN_AT).do(daily_refresh)
    while True:
        schedule.run_pending()
        time.sleep(60)
