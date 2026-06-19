# Vancouver & Squamish Live Music Scanner

A simple web app that tracks live music shows in Vancouver and Squamish, filtered to your preferences.

## Features

- **Auto-updated daily** via GitHub Actions
- **Mobile-friendly** dark theme
- **Filter by location** (Vancouver / Squamish / All)
- **Your genres**: rock, folk, indie, country, alt-country, punk
- **Filters out**: metal, rap, EDM, techno, house

## Venues Tracked

### Vancouver
Red Gate, Green Auto, Fox Cabaret, Biltmore, Vogue, Lido, Commodore Ballroom, Guilt & Co, Lanalou's, The Cobalt, The Heatley, Orpheum Theatre, Rickshaw Theatre

### Squamish
Brackendale Art Gallery, Trickster's Hideout, The Backyard

## Data Sources

- **Songkick** (primary) — Vancouver metro area
- **Eventbrite** — Trickster's Hideout
- **Direct scraping** — The Backyard, Brackendale Art Gallery

## Setup

### GitHub Pages

1. Push this directory to a GitHub repo
2. Enable GitHub Pages in Settings → Pages → Source: `main` branch, `/` root
3. The GitHub Action will run daily at 4am PT to update events

### Local Development

```bash
# Generate fresh data
python3 generate-json.py

# Serve locally
python3 -m http.server 8000
# Open http://localhost:8000
```

## Files

- `index.html` — Web app (static, no build needed)
- `scanner.py` — Python scraper (same as `/scripts/show-scanner.py`)
- `generate-json.py` — Converts scraper output to JSON
- `.github/workflows/update-events.yml` — Daily update action
- `data/events.json` — Event data (auto-generated)

## Manual Update

Trigger via GitHub Actions UI (Actions → Update Events → Run workflow)

## Limitations

- Squamish venues have limited data exposure (Eventbrite/small sites)
- Some shows may be missed if not listed on tracked platforms
- Genre filtering is keyword-based (some edge cases may slip through)

## Maintenance

If you notice missing shows or want to adjust filters:

1. Edit `scanner.py` (venues, genres, exclusions)
2. Test locally: `python3 generate-json.py`
3. Commit changes — GitHub Action will pick them up

---

Built with vanilla JS, Python, and GitHub Actions. No frameworks, no build step.
