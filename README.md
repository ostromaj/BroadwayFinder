# Cheap Broadway Ticket Finder

A free static website that shows NYC + DC theater tickets ranked by lowest available price.

## How it works

- `index.html`, `style.css`, and `script.js` create the website.
- `scripts/fetch_tickets.py` fetches ticket data.
- GitHub Actions refreshes `data/tickets.json` every 6 hours.
- GitHub Pages hosts the site for free.

## Important note about scraping

This starter app does **not** bypass anti-bot systems, CAPTCHAs, logins, paywalls, or website restrictions. Use official APIs or pages that allow automated access. For sources without public APIs, add manual links or use an approved affiliate/data feed.

## Setup

1. Create a GitHub repo, for example: `cheap-broadway-tickets`.
2. Upload these files.
3. Go to the repo's **Settings → Secrets and variables → Actions**.
4. Add:
   - `SEATGEEK_CLIENT_ID`
   - `TICKETMASTER_API_KEY`
5. Go to **Actions** and run `Refresh ticket data`.
6. Go to **Settings → Pages**.
7. Set source to your main branch and root folder.
8. Your site will be live at:

`https://YOUR-GITHUB-USERNAME.github.io/cheap-broadway-tickets/`

## Sources currently included

- SeatGeek API
- Ticketmaster Discovery API

## Future add-ons

- TodayTix manual/deep-link source
- TKTS daily manual source
- Seat quality score
- Show image posters
- DC-only / NYC-only landing pages
- Price history tracking
