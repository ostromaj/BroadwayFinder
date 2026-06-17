import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
OUTFILE = DATA_DIR / "tickets.json"

NYC_COORDS = {"lat": 40.7128, "lon": -74.0060}
DC_COORDS = {"lat": 38.9072, "lon": -77.0369}

BROADWAY_KEYWORDS = [
    "broadway",
    "musical",
    "theater",
    "theatre",
]

def safe_get_json(url, params=None, headers=None, timeout=20):
    headers = headers or {
        "User-Agent": "BroadwayTicketFinder/1.0 personal research project; contact: your-email@example.com"
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        print(f"Request failed: {url} {exc}")
        return None

def fetch_seatgeek(city_key, lat, lon):
    """
    SeatGeek has a public developer API.
    Add your SEATGEEK_CLIENT_ID as a GitHub Actions secret.
    Docs: https://platform.seatgeek.com/
    """
    client_id = os.getenv("SEATGEEK_CLIENT_ID")
    if not client_id:
        print("Skipping SeatGeek: missing SEATGEEK_CLIENT_ID")
        return []

    url = "https://api.seatgeek.com/2/events"
    params = {
        "client_id": client_id,
        "lat": lat,
        "lon": lon,
        "range": "35mi",
        "per_page": 100,
        "taxonomies.name": "theater",
        "datetime_utc.gte": datetime.now(timezone.utc).isoformat(),
    }

    data = safe_get_json(url, params=params)
    if not data:
        return []

    tickets = []
    for event in data.get("events", []):
        stats = event.get("stats") or {}
        venue = event.get("venue") or {}
        lowest = stats.get("lowest_price")

        if lowest is None:
            continue

        dt = event.get("datetime_local", "")
        date = dt[:10] if dt else ""
        time = dt[11:16] if len(dt) >= 16 else ""

        tickets.append({
            "show": event.get("title", "Unknown show"),
            "city": city_key,
            "venue": venue.get("name", ""),
            "date": date,
            "time": time,
            "price": lowest,
            "section": "",
            "source": "SeatGeek",
            "url": event.get("url", ""),
        })

    return tickets

def fetch_ticketmaster(city_key, lat, lon):
    """
    Ticketmaster Discovery API can find events.
    Add TICKETMASTER_API_KEY as a GitHub Actions secret.
    Note: this may provide event discovery/pricing ranges, not always exact live seat inventory.
    """
    api_key = os.getenv("TICKETMASTER_API_KEY")
    if not api_key:
        print("Skipping Ticketmaster: missing TICKETMASTER_API_KEY")
        return []

    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey": api_key,
        "latlong": f"{lat},{lon}",
        "radius": 35,
        "unit": "miles",
        "classificationName": "theatre",
        "size": 100,
        "sort": "date,asc",
    }

    data = safe_get_json(url, params=params)
    if not data:
        return []

    events = data.get("_embedded", {}).get("events", [])
    tickets = []

    for event in events:
        price_ranges = event.get("priceRanges") or []
        if not price_ranges:
            continue

        lowest = min([p.get("min") for p in price_ranges if p.get("min") is not None], default=None)
        if lowest is None:
            continue

        dates = event.get("dates", {}).get("start", {})
        venue = (event.get("_embedded", {}).get("venues") or [{}])[0]

        tickets.append({
            "show": event.get("name", "Unknown show"),
            "city": city_key,
            "venue": venue.get("name", ""),
            "date": dates.get("localDate", ""),
            "time": dates.get("localTime", "")[:5] if dates.get("localTime") else "",
            "price": lowest,
            "section": "",
            "source": "Ticketmaster",
            "url": event.get("url", ""),
        })

    return tickets

def add_manual_sources():
    """
    Use this for sources that do not provide reliable public APIs.
    Do not bypass anti-bot systems, logins, CAPTCHAs, paywalls, or robots.txt.
    Add links/results manually if needed.
    """
    return [
        # Example:
        # {
        #   "show": "Example Show",
        #   "city": "nyc",
        #   "venue": "Example Theatre",
        #   "date": "2026-06-17",
        #   "time": "19:00",
        #   "price": 59,
        #   "section": "Balcony",
        #   "source": "Manual/TKTS",
        #   "url": "https://example.com"
        # }
    ]

def dedupe(tickets):
    seen = set()
    clean = []
    for t in tickets:
        key = (
            t.get("show", "").lower(),
            t.get("city"),
            t.get("date"),
            t.get("time"),
            t.get("source"),
            str(t.get("price")),
        )
        if key not in seen:
            seen.add(key)
            clean.append(t)
    return clean

def main():
    tickets = []
    tickets += fetch_seatgeek("nyc", NYC_COORDS["lat"], NYC_COORDS["lon"])
    tickets += fetch_seatgeek("dc", DC_COORDS["lat"], DC_COORDS["lon"])
    tickets += fetch_ticketmaster("nyc", NYC_COORDS["lat"], NYC_COORDS["lon"])
    tickets += fetch_ticketmaster("dc", DC_COORDS["lat"], DC_COORDS["lon"])
    tickets += add_manual_sources()

    tickets = dedupe(tickets)
    tickets.sort(key=lambda x: float(x.get("price") or 999999))

    payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "tickets": tickets,
    }

    OUTFILE.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(tickets)} tickets to {OUTFILE}")

if __name__ == "__main__":
    main()
