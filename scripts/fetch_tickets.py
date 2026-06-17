import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
OUTFILE = DATA_DIR / "tickets.json"

CITIES = {
    "nyc": {
        "name": "New York",
        "lat": 40.7128,
        "lon": -74.0060,
        "ticketmaster_city": "New York"
    },
    "dc": {
        "name": "Washington DC",
        "lat": 38.9072,
        "lon": -77.0369,
        "ticketmaster_city": "Washington"
    }
}

def get_json(url, params):
    try:
        r = requests.get(url, params=params, timeout=20)
        print("URL:", r.url)
        print("Status:", r.status_code)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("FAILED:", e)
        return {}

def fetch_ticketmaster(city_key, info):
    api_key = os.getenv("TICKETMASTER_API_KEY")
    if not api_key:
        print("Missing TICKETMASTER_API_KEY")
        return []

    url = "https://app.ticketmaster.com/discovery/v2/events.json"

    params = {
        "apikey": api_key,
        "city": info["ticketmaster_city"],
        "countryCode": "US",
        "classificationName": "Theatre",
        "size": 200,
        "sort": "date,asc"
    }

    data = get_json(url, params)
    events = data.get("_embedded", {}).get("events", [])

    tickets = []

    for event in events:
        name = event.get("name", "Unknown Show")
        dates = event.get("dates", {}).get("start", {})
        venues = event.get("_embedded", {}).get("venues", [{}])
        venue = venues[0] if venues else {}

        price_ranges = event.get("priceRanges", [])
        prices = [
            p.get("min")
            for p in price_ranges
            if p.get("min") is not None
        ]

        lowest_price = min(prices) if prices else None

        # If no price listed, still include the event so your site is not empty.
        if lowest_price is None:
            lowest_price = 999

        image = ""
        images = event.get("images", [])
        if images:
            image = images[0].get("url", "")

        tickets.append({
            "show": name,
            "city": city_key,
            "venue": venue.get("name", ""),
            "date": dates.get("localDate", ""),
            "time": dates.get("localTime", "")[:5] if dates.get("localTime") else "",
            "price": lowest_price,
            "section": "Best Available",
            "source": "Ticketmaster",
            "url": event.get("url", ""),
            "image": image
        })

    return tickets

def fetch_seatgeek(city_key, info):
    client_id = os.getenv("SEATGEEK_CLIENT_ID")
    if not client_id:
        print("Missing SEATGEEK_CLIENT_ID")
        return []

    url = "https://api.seatgeek.com/2/events"

    params = {
        "client_id": client_id,
        "lat": info["lat"],
        "lon": info["lon"],
        "range": "35mi",
        "per_page": 200,
        "q": "theater",
        "sort": "datetime_local.asc"
    }

    data = get_json(url, params)
    events = data.get("events", [])

    tickets = []

    for event in events:
        stats = event.get("stats", {})
        venue = event.get("venue", {})

        lowest_price = stats.get("lowest_price")

        if lowest_price is None:
            continue

        dt = event.get("datetime_local", "")
        date = dt[:10] if dt else ""
        time = dt[11:16] if len(dt) >= 16 else ""

        performers = event.get("performers", [])
        image = ""
        if performers:
            image = performers[0].get("image", "")

        tickets.append({
            "show": event.get("title", "Unknown Show"),
            "city": city_key,
            "venue": venue.get("name", ""),
            "date": date,
            "time": time,
            "price": lowest_price,
            "section": "Best Available",
            "source": "SeatGeek",
            "url": event.get("url", ""),
            "image": image
        })

    return tickets

def dedupe(tickets):
    seen = set()
    cleaned = []

    for t in tickets:
        key = (
            t.get("show", "").lower(),
            t.get("city"),
            t.get("venue", "").lower(),
            t.get("date"),
            t.get("time"),
            t.get("source")
        )

        if key not in seen:
            seen.add(key)
            cleaned.append(t)

    return cleaned

def main():
    tickets = []

    for city_key, info in CITIES.items():
        print(f"Fetching Ticketmaster for {city_key}")
        tickets.extend(fetch_ticketmaster(city_key, info))

        print(f"Fetching SeatGeek for {city_key}")
        tickets.extend(fetch_seatgeek(city_key, info))

    tickets = dedupe(tickets)

    tickets.sort(key=lambda x: float(x.get("price") or 999999))

    payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "tickets": tickets
    }

    OUTFILE.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(tickets)} tickets to {OUTFILE}")

if __name__ == "__main__":
    main()
