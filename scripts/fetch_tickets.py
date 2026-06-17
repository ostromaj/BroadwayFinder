import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
OUTFILE = DATA_DIR / "tickets.json"

API_KEY = os.getenv("TICKETMASTER_API_KEY")
DAYS_AHEAD = 10

SEARCHES = [
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Hamilton"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Wicked"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "The Lion King"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Moulin Rouge"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Hadestown"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Chicago"},
    {"city": "nyc", "cityName": "New York", "stateCode": "NY", "keyword": "Aladdin"},
    {"city": "dc", "cityName": "Washington", "stateCode": "DC", "keyword": "Kennedy Center"},
    {"city": "dc", "cityName": "Washington", "stateCode": "DC", "keyword": "Musical"},
]

def tm_time(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def get_api_price(event):
    ranges = event.get("priceRanges") or []
    prices = [float(p["min"]) for p in ranges if p.get("min") is not None]
    return min(prices) if prices else None

def get_image(event):
    images = event.get("images") or []
    if not images:
        return ""
    images = sorted(images, key=lambda x: x.get("width", 0), reverse=True)
    return images[0].get("url", "")

def extract_page_prices(url):
    """
    Attempts to find dollar amounts from normal returned HTML.
    This will only work if the prices are actually present in the page HTML.
    It will not work for prices loaded later by JavaScript.
    """
    try:
        headers = {
            "User-Agent": "BroadwayFinder personal ticket research tool"
        }

        response = requests.get(url, headers=headers, timeout=20)

        if response.status_code != 200:
            return None, None, 0

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        matches = re.findall(r"\$\d+(?:,\d{3})*(?:\.\d{2})?", text)

        prices = []
        for m in matches:
            try:
                value = float(m.replace("$", "").replace(",", ""))
                if 5 <= value <= 5000:
                    prices.append(value)
            except ValueError:
                pass

        if not prices:
            return None, None, 0

        return min(prices), max(prices), len(prices)

    except Exception as e:
        print("Page price check failed:", url, e)
        return None, None, 0

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

    response = requests.get(url, params=params, timeout=25)
    print("SEARCH:", search["keyword"], search["cityName"], response.status_code)

    if response.status_code != 200:
        print(response.text[:1000])
        return []

    data = response.json()
    events = data.get("_embedded", {}).get("events", [])

    tickets = []

    for event in events:
        event_url = event.get("url", "")
        api_price = get_api_price(event)

        page_low, page_high, page_count = extract_page_prices(event_url)

        best_price = api_price or page_low

        if best_price is None:
            price_display = "Check live price"
            sort_price = 999999
        else:
            price_display = f"${best_price:.2f}"
            sort_price = best_price

        dates = event.get("dates", {}).get("start", {})
        venue = (event.get("_embedded", {}).get("venues") or [{}])[0]

        tickets.append({
            "show": event.get("name", "Unknown Show"),
            "city": search["city"],
            "venue": venue.get("name", ""),
            "date": dates.get("localDate", ""),
            "time": (dates.get("localTime") or "")[:5],
            "price": best_price,
            "price_display": price_display,
            "lowest_page_price": page_low,
            "highest_page_price": page_high,
            "prices_found_on_page": page_count,
            "sort_price": sort_price,
            "section": "Best Available",
            "source": "Ticketmaster",
            "url": event_url,
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
        )

        if key not in seen:
            seen.add(key)
            output.append(t)

    return output

def main():
    tickets = []

    for search in SEARCHES:
        tickets.extend(fetch_ticketmaster(search))

    tickets = dedupe(tickets)
    tickets.sort(key=lambda x: (x["sort_price"], x["date"], x["time"]))

    payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "days_ahead": DAYS_AHEAD,
        "tickets": tickets,
    }

    OUTFILE.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(tickets)} events to {OUTFILE}")

if __name__ == "__main__":
    main()
