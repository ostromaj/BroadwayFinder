import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
OUTFILE = DATA_DIR / "tickets.json"

API_KEY = os.getenv("TICKETMASTER_API_KEY")

SEARCHES = [
    {"city": "nyc", "keyword": "Broadway", "stateCode": "NY"},
    {"city": "nyc", "keyword": "Musical", "stateCode": "NY"},
    {"city": "nyc", "keyword": "Theatre", "stateCode": "NY"},
    {"city": "dc", "keyword": "Musical", "stateCode": "DC"},
    {"city": "dc", "keyword": "Theatre", "stateCode": "DC"},
    {"city": "dc", "keyword": "Kennedy Center", "stateCode": "DC"},
]

def get_price(event):
    ranges = event.get("priceRanges") or []
    prices = [p.get("min") for p in ranges if p.get("min") is not None]
    return min(prices) if prices else None

def get_image(event):
    images = event.get("images") or []
    if not images:
        return ""
    images = sorted(images, key=lambda img: img.get("width", 0), reverse=True)
    return images[0].get("url", "")

def fetch_ticketmaster(search):
    if not API_KEY:
        raise RuntimeError("Missing TICKETMASTER_API_KEY GitHub secret.")

    url = "https://app.ticketmaster.com/discovery/v2/events.json"

    params = {
        "apikey": API_KEY,
        "countryCode": "US",
        "stateCode": search["stateCode"],
        "keyword": search["keyword"],
        "classificationName": "Theatre",
        "size": 200,
        "sort": "date,asc",
    }

    print("Searching:", search)

    response = requests.get(url, params=params, timeout=25)
    print("Status:", response.status_code)
    print("URL:", response.url)

    if response.status_code != 200:
        print(response.text[:1000])
        return []

    data = response.json()
    events = data.get("_embedded", {}).get("events", [])

    tickets = []

    for event in events:
        price = get_price(event)

        # Skip events without a real listed price.
        if price is None:
            continue

        dates = event.get("dates", {}).get("start", {})
        venue = (event.get("_embedded", {}).get("venues") or [{}])[0]

        tickets.append({
            "show": event.get("name", "Unknown Show"),
            "city": search["city"],
            "venue": venue.get("name", ""),
            "date": dates.get("localDate", ""),
            "time": (dates.get("localTime") or "")[:5],
            "price": price,
            "section": "Best Available",
            "source": "Ticketmaster",
            "url": event.get("url", ""),
            "image": get_image(event),
        })

    return tickets

def dedupe(tickets):
    seen = set()
    output = []

    for t in tickets:
        key = (
            t["show"].lower(),
            t["city"],
            t["venue"].lower(),
            t["date"],
            t["time"],
            t["price"],
        )

        if key not in seen:
            seen.add(key)
            output.append(t)

    return output

def main():
    all_tickets = []

    for search in SEARCHES:
        all_tickets.extend(fetch_ticketmaster(search))

    all_tickets = dedupe(all_tickets)
    all_tickets.sort(key=lambda x: float(x["price"]))

    payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "tickets": all_tickets,
    }

    OUTFILE.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(all_tickets)} live tickets to {OUTFILE}")

if __name__ == "__main__":
    main()
