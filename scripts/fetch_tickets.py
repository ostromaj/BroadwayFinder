import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
OUTFILE = DATA_DIR / "tickets.json"

API_KEY = os.getenv("TICKETMASTER_API_KEY")
DAYS_AHEAD = 10

SEARCHES = [
    # Broad NYC searches
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Broadway"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Musical"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Theatre"},

    # Specific major NYC shows
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Hamilton"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Wicked"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "The Lion King"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Moulin Rouge"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Hadestown"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Chicago"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Book of Mormon"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Aladdin"},

    # DC searches
    {"city": "dc", "cityName": "Washington", "stateCode": "DC", "keyword": "Musical"},
    {"city": "dc", "cityName": "Washington", "stateCode": "DC", "keyword": "Theatre"},
    {"city": "dc", "cityName": "Washington", "stateCode": "DC", "keyword": "Kennedy Center"},
    {"city": "dc", "cityName": "Washington", "stateCode": "DC", "keyword": "Broadway"},
]

def tm_time(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def get_price(event):
    ranges = event.get("priceRanges") or []
    prices = []

    for p in ranges:
        if p.get("min") is not None:
            prices.append(float(p["min"]))

    return min(prices) if prices else None

def get_image(event):
    images = event.get("images") or []
    if not images:
        return ""

    images = sorted(images, key=lambda x: x.get("width", 0), reverse=True)
    return images[0].get("url", "")

def fetch_ticketmaster(search):
    if not API_KEY:
        raise RuntimeError("Missing TICKETMASTER_API_KEY GitHub secret.")

    now = datetime.now(timezone.utc)
    end = now + timedelta(days=DAYS_AHEAD)

    url = "https://app.ticketmaster.com/discovery/v2/events.json"

    params = {
        "apikey": API_KEY,
        "countryCode": "US",
        "city": search["cityName"],
        "stateCode": search["stateCode"],
        "keyword": search["keyword"],
        "segmentName": "Arts & Theatre",
        "startDateTime": tm_time(now),
        "endDateTime": tm_time(end),
        "size": 200,
        "sort": "date,asc",
    }

    print("\nSEARCH:", search)
    response = requests.get(url, params=params, timeout=25)
    print("Status:", response.status_code)
    print("URL:", response.url)

    if response.status_code != 200:
        print(response.text[:1000])
        return []

    data = response.json()
    events = data.get("_embedded", {}).get("events", [])
    print("Events returned:", len(events))

    tickets = []

    for event in events:
        price = get_price(event)

        # Ticketmaster often returns events but no public price range.
        # We skip those because you asked for real live prices only.
        if price is None:
            print("Skipped no price:", event.get("name"))
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
        "days_ahead": DAYS_AHEAD,
        "tickets": all_tickets,
    }

    OUTFILE.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {len(all_tickets)} live priced tickets to {OUTFILE}")

if __name__ == "__main__":
    main()
