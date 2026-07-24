#!/usr/bin/env python3
"""
Show Scanner - Weekly music event digest for Alex

Scans:
- Songkick (Vancouver metro) - filtered by venue + genre
- Trickster's Hideout (Squamish) - via Eventbrite
- The Backyard (Squamish) - direct site
- Brackendale Art Gallery - direct site

Outputs markdown digest for Telegram delivery.
"""

import html
import json
from pathlib import Path
import re
import sys
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError
from zoneinfo import ZoneInfo


# === Configuration ===

VANCOUVER_VENUES = {
    "red-gate": "Red Gate",
    "green-auto": "Green Auto", 
    "fox-cabaret": "Fox Cabaret",
    "biltmore-cabaret": "Biltmore Cabaret",
    "biltmore": "Biltmore",
    "vogue-theatre": "Vogue Theatre",
    "lido": "The Lido",
    "commodore-ballroom": "Commodore Ballroom",
    "guilt-co": "Guilt & Co",
    "lanalous": "Lanalou's",
    "cobalt": "The Cobalt",
    "heatley": "The Heatley",
    "orpheum-theatre": "Orpheum Theatre",
    "orpheum": "Orpheum",
    "rickshaw-theatre": "Rickshaw Theatre",
}

SQUAMISH_VENUES = {
    "brackendale-art-gallery": "Brackendale Art Gallery",
    "tricksters-hideout": "Trickster's Hideout",
    "the-backyard": "The Backyard",
}

# Keywords to exclude (metal, rap, EDM, etc.)
EXCLUDE_KEYWORDS = {
    "metal", "death metal", "black metal", "thrash metal", "doom metal",
    "hip hop", "hip-hop", "rap", "rapper", "trap",
    "edm", "techno", "house", "dubstep", "dnb", "drum and bass", "trance",
    "dj set", "club night"
}

# Specific artists/bands to exclude (metal, etc.)
EXCLUDE_ARTISTS = {
    "six feet under", "cattle decapitation", "iron kingdom", "jinjer", "kamelot",
    "uada", "dungeon serpent", "castle"  # metal bands
}

WEEKS_AHEAD = 6
LOCAL_TZ = ZoneInfo("America/Vancouver")
ROOT_DIR = Path(__file__).resolve().parents[2]
SPOTIFY_PROFILE_PATH = ROOT_DIR / "apps/show-scanner/data/spotify_profile.json"
SPOTIFY_RELATED_PATH = ROOT_DIR / "apps/show-scanner/data/spotify_related_artists.json"


# === Utilities ===

def fetch_url(url, timeout=15):
    """Fetch URL content with basic error handling."""
    try:
        req = Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        with urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="ignore")
    except (URLError, TimeoutError) as e:
        print(f"[WARN] Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def clean_artist_name(slug):
    """Convert URL slug to proper artist name."""
    # Remove 'at-venue' suffix
    if '-at-' in slug:
        slug = slug.split('-at-')[0]
    # Convert hyphens to spaces and title case
    name = slug.replace('-', ' ')
    # Handle common patterns
    name = re.sub(r'\band\b', '&', name, flags=re.IGNORECASE)
    # Title case but preserve all-caps like "DJ"
    words = name.split()
    result = []
    for word in words:
        if word.upper() in ['DJ', 'MC', 'NYC', 'LA', 'UK', 'BC']:
            result.append(word.upper())
        else:
            result.append(word.title())
    return ' '.join(result)


def should_exclude(text):
    """Check if text contains exclusion keywords or is a known excluded artist."""
    text_lower = text.lower().strip()
    
    # Check exact artist matches first
    if text_lower in EXCLUDE_ARTISTS:
        return True
    
    # Check keyword patterns
    for kw in EXCLUDE_KEYWORDS:
        if kw in text_lower:
            return True
    
    return False


def venue_matches(venue_slug):
    """Check if venue slug matches our target venues."""
    venue_lower = venue_slug.lower()
    for slug in VANCOUVER_VENUES:
        if slug in venue_lower:
            return VANCOUVER_VENUES[slug]
    for slug in SQUAMISH_VENUES:
        if slug in venue_lower:
            return SQUAMISH_VENUES[slug]
    return None


def parse_event_date(date_str):
    """Parse supported event date formats to a date object."""
    for fmt in ("%B %d, %Y", "%Y-%m-%d", "%b %d, %Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def filter_events_to_window(events, today=None, weeks_ahead=WEEKS_AHEAD):
    """Keep only upcoming dated events inside the scan window; keep undated items."""
    today = today or datetime.now(LOCAL_TZ).date()
    window_end = today + timedelta(weeks=weeks_ahead)
    filtered = []

    for event in events:
        event_date = parse_event_date(event.get("date", ""))
        if event_date is None or today <= event_date <= window_end:
            filtered.append(event)

    return filtered


def normalize_artist_name(name):
    """Normalize artist names for matching."""
    normalized = (name or "").strip().lower()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def split_event_artist_candidates(artist_text):
    """Split lineup-style artist strings into individual candidates."""
    text = html.unescape(artist_text or "")
    text = re.sub(r"\s+\band\b\s+", " • ", text, flags=re.IGNORECASE)
    parts = re.split(r"\s*[•/,]\s*", text)
    candidates = []
    for part in parts:
        clean = re.sub(r"\s*\([^)]*\)\s*", " ", part).strip()
        normalized = normalize_artist_name(clean)
        if normalized:
            candidates.append((clean, normalized))
    return candidates


def load_spotify_profile(profile_path=SPOTIFY_PROFILE_PATH):
    """Load Spotify-derived artist weights if available."""
    if not profile_path.exists():
        return []

    try:
        data = json.loads(profile_path.read_text())
    except json.JSONDecodeError:
        print(f"[WARN] Could not parse Spotify profile at {profile_path}", file=sys.stderr)
        return []

    artists = []
    for entry in data.get("artists", []):
        artist = (entry.get("artist") or "").strip()
        normalized = entry.get("artist_normalized") or normalize_artist_name(artist)
        weight = float(entry.get("weight") or 0)
        if artist and normalized and len(normalized) >= 4:
            artists.append({
                "artist": artist,
                "artist_normalized": normalized,
                "weight": weight,
            })
    return artists


def load_related_artist_index(index_path=SPOTIFY_RELATED_PATH):
    """Load cached related-artist map if available."""
    if not index_path.exists():
        return {}

    try:
        data = json.loads(index_path.read_text())
    except json.JSONDecodeError:
        print(f"[WARN] Could not parse related artist cache at {index_path}", file=sys.stderr)
        return {}

    return data.get("related_index", {}) or {}


def score_event_interest(event, spotify_profile, related_index=None):
    """Score an event against the Spotify-derived taste profile."""
    related_index = related_index or {}
    if not spotify_profile:
        event["interest_score"] = 0
        event["matched_artists"] = []
        event["interest_reason"] = ""
        event["score_breakdown"] = []
        return event

    candidates = split_event_artist_candidates(event.get("artist", ""))
    candidate_norms = {normalized for _, normalized in candidates}
    full_text = normalize_artist_name(event.get("artist", ""))
    matches = []
    breakdown = []

    for profile_artist in spotify_profile:
        name_norm = profile_artist["artist_normalized"]
        if name_norm in candidate_norms:
            matches.append(profile_artist)
            continue
        if len(name_norm) >= 8 and f" {name_norm} " in f" {full_text} ":
            matches.append(profile_artist)

    unique_matches = []
    seen = set()
    for match in sorted(matches, key=lambda item: item["weight"], reverse=True):
        if match["artist_normalized"] not in seen:
            seen.add(match["artist_normalized"])
            unique_matches.append(match)

    if not unique_matches:
        related_matches = []
        for display_name, normalized in candidates:
            for relation in related_index.get(normalized, []):
                related_matches.append({
                    "event_artist": display_name,
                    **relation,
                })

        if not related_matches:
            event["interest_score"] = 0
            event["matched_artists"] = []
            event["interest_reason"] = ""
            event["score_breakdown"] = []
            return event

        dedup_related = []
        seen_related = set()
        for relation in sorted(related_matches, key=lambda item: (-item["related_score"], item["rank"], item["seed_artist"].lower())):
            key = (normalize_artist_name(relation["event_artist"]), relation["seed_artist"].lower())
            if key in seen_related:
                continue
            seen_related.add(key)
            dedup_related.append(relation)

        top_related = dedup_related[0]
        base_score = min(59, round(top_related["related_score"] + max(0, len(dedup_related) - 1) * 4))
        event["interest_score"] = base_score
        event["matched_artists"] = [item["event_artist"] for item in dedup_related]
        seeds = [item["seed_artist"] for item in dedup_related[:3]]
        event["interest_reason"] = f"Related to your Spotify history via {', '.join(seeds)}"
        for relation in dedup_related[:5]:
            breakdown.append({
                "type": "related_artist",
                "points": round(relation["related_score"], 2),
                "artist": relation["event_artist"],
                "seed_artist": relation["seed_artist"],
                "rank": relation["rank"],
                "detail": f"{relation['event_artist']} is similar to {relation['seed_artist']} (rank {relation['rank']} on cached similar-artists list)",
            })
        event["score_breakdown"] = breakdown
        return event

    base_score = min(100, round(60 + (unique_matches[0]["weight"] * 0.4) + max(0, len(unique_matches) - 1) * 8))
    event["interest_score"] = base_score
    event["matched_artists"] = [match["artist"] for match in unique_matches]
    event["interest_reason"] = f"Matches your Spotify history: {', '.join(event['matched_artists'][:3])}"
    for match in unique_matches[:5]:
        breakdown.append({
            "type": "direct_history_match",
            "points": round(60 + (match["weight"] * 0.4), 2),
            "artist": match["artist"],
            "detail": f"Direct match from your Spotify history ({match['artist']})",
        })
    event["score_breakdown"] = breakdown
    return event


def enrich_events_with_preferences(events, spotify_profile, related_index=None):
    """Annotate events with direct artist matches from the Spotify profile."""
    enriched = []
    for event in events:
        enriched.append(score_event_interest(dict(event), spotify_profile, related_index=related_index))
    return enriched


# === Scrapers ===

def scrape_songkick():
    """Scrape Songkick Vancouver metro for upcoming shows at target venues."""
    events = []
    base_url = "https://www.songkick.com/metro-areas/27398-canada-vancouver"
    
    for page in range(1, 5):  # First 4 pages
        url = f"{base_url}?page={page}" if page > 1 else base_url
        page_html = fetch_url(url)
        if not page_html:
            continue
        
        # Track current date from HTML structure
        current_date = None
        
        # Find date headers
        date_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d+)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})'
        
        # Build a map of concert IDs to their full artist names from <strong> tags
        # Pattern: <a class="event-link" href="/concerts/43062105-avro-at-green-auto">
        #            <span><strong>Avro, DIELECTRIC, EARS (BC), and Wack</strong></span>
        artist_map = {}
        event_link_pattern = r'<a[^>]*href="/concerts/(\d+)-[^"]+at-([^"]+)"[^>]*>\s*(?:<span>)?\s*<strong>([^<]+)</strong>'
        for match in re.finditer(event_link_pattern, page_html, re.IGNORECASE | re.DOTALL):
            concert_id = match.group(1)
            venue_slug = match.group(2).lower()
            full_lineup = html.unescape(match.group(3).strip())
            artist_map[concert_id] = {
                "lineup": full_lineup,
                "venue_slug": venue_slug
            }
        
        # Process HTML line by line to track dates and match events
        lines = page_html.split('\n')
        for line in lines:
            # Check for date header
            date_match = re.search(date_pattern, line)
            if date_match:
                day_name, day, month, year = date_match.groups()
                current_date = f"{month} {day}, {year}"
            
            # Check for concert links on this line
            link_match = re.search(r'/concerts/(\d+)-[a-z0-9-]+-at-([a-z0-9-]+)', line.lower())
            if link_match and current_date:
                concert_id = link_match.group(1)
                venue_slug = link_match.group(2)
                
                # Check if venue matches our list
                venue_name = venue_matches(venue_slug)
                if venue_name:
                    # Get full lineup from artist_map, fallback to URL slug
                    if concert_id in artist_map:
                        artist_name = artist_map[concert_id]["lineup"]
                    else:
                        # Fallback: extract from URL slug
                        slug_match = re.search(r'/concerts/\d+-(.+?)-at-', line.lower())
                        if slug_match:
                            artist_name = clean_artist_name(slug_match.group(1))
                        else:
                            continue
                    
                    # Skip if excluded genre/style
                    if should_exclude(artist_name):
                        continue
                    
                    events.append({
                        "date": current_date,
                        "artist": artist_name,
                        "venue": venue_name,
                        "link": f"https://www.songkick.com/concerts/{concert_id}",
                        "source": "Songkick"
                    })
    
    # Dedupe within Songkick (same concert ID can appear multiple times)
    seen_ids = set()
    unique_events = []
    for e in events:
        concert_id = e["link"].split("/")[-1]
        if concert_id not in seen_ids:
            seen_ids.add(concert_id)
            unique_events.append(e)
    
    return unique_events


def scrape_eventbrite_tricksters():
    """Scrape Trickster's Hideout events from Eventbrite."""
    events = []
    
    # Try the organizer page
    url = "https://www.eventbrite.ca/o/tricksters-hideout-74359195093"
    page_html = fetch_url(url)
    if not page_html:
        return events
    
    # Eventbrite embeds event data - look for the structured data
    # Pattern: data-event-id with nearby event title
    # Also look for event cards with titles
    
    # Look for event links with titles - usually in format:
    # <a href="/e/event-name-tickets-123456" ... >Event Name</a>
    event_link_pattern = r'href="/e/([^"]+)"[^>]*>([^<]+)</a>'
    matches = re.findall(event_link_pattern, page_html)
    
    for slug, title in matches:
        clean_title = html.unescape(title.strip())
        # Skip navigation links and organizer names
        if clean_title.lower() in ["trickster's hideout", "tricksters hideout", "view details"]:
            continue
        if len(clean_title) < 3:
            continue
        if not should_exclude(clean_title):
            # Try to extract date from the slug or nearby text
            events.append({
                "date": "TBD",
                "artist": clean_title,
                "venue": "Trickster's Hideout",
                "source": "Eventbrite"
            })
    
    # Also try JSON-LD if present
    json_ld_pattern = r'<script type="application/ld\+json">([^<]+)</script>'
    json_matches = re.findall(json_ld_pattern, page_html)
    
    for json_str in json_matches:
        try:
            data = json.loads(json_str)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "Event":
                    name = item.get("name", "")
                    # Skip if it's just the venue name
                    if name.lower() in ["trickster's hideout", "tricksters hideout"]:
                        continue
                    start = item.get("startDate", "")
                    if start:
                        try:
                            dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                            date_str = dt.strftime("%B %d, %Y")
                        except:
                            date_str = start[:10]
                    else:
                        date_str = "TBD"
                    
                    if name and not should_exclude(name):
                        # Update existing TBD entry or add new
                        found = False
                        for e in events:
                            if e['artist'].lower() == name.lower():
                                e['date'] = date_str
                                found = True
                                break
                        if not found:
                            events.append({
                                "date": date_str,
                                "artist": html.unescape(name),
                                "venue": "Trickster's Hideout",
                                "source": "Eventbrite"
                            })
        except json.JSONDecodeError:
            pass
    
    return events


def scrape_backyard():
    """Scrape The Backyard Squamish events."""
    events = []
    
    # Try events calendar page
    url = "https://www.backyardsquamish.com/c"
    page_html = fetch_url(url)
    if not page_html:
        return events
    
    # Look for JSON-LD structured data
    json_ld_pattern = r'<script type="application/ld\+json">([^<]+)</script>'
    json_matches = re.findall(json_ld_pattern, page_html)
    
    for json_str in json_matches:
        try:
            data = json.loads(json_str)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "Event":
                    start = item.get("startDate", "")
                    if start:
                        try:
                            dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                            date_str = dt.strftime("%B %d, %Y")
                        except:
                            date_str = start[:10]
                    else:
                        date_str = "TBD"
                    
                    name = item.get("name", "Unknown Event")
                    if not should_exclude(name):
                        events.append({
                            "date": date_str,
                            "artist": html.unescape(name),
                            "venue": "The Backyard",
                            "source": "Backyard Squamish"
                        })
        except json.JSONDecodeError:
            pass
    
    # Look for event titles in HTML - The Backyard likely has simple event cards
    # Pattern: "Live at The Backyard" or event names in headers/titles
    title_patterns = [
        r'<h[1-4][^>]*>([^<]+(?:Live|Music|Concert)[^<]*)</h[1-4]>',
        r'<div[^>]*class="[^"]*event[^"]*"[^>]*>.*?<[^>]+>([^<]+)</[^>]+>',
    ]
    
    for pattern in title_patterns:
        matches = re.findall(pattern, page_html, re.IGNORECASE | re.DOTALL)
        for title in matches[:10]:
            clean = html.unescape(title.strip())
            # Skip generic text and metadata noise
            if clean and len(clean) > 5 and len(clean) < 100:
                if 'content=' not in clean and '/>' not in clean:
                    if not should_exclude(clean):
                        if not any(e['artist'].lower() == clean.lower() for e in events):
                            events.append({
                                "date": "TBD",
                                "artist": clean,
                                "venue": "The Backyard",
                                "source": "Backyard Squamish"
                            })
    
    return events


def scrape_brackendale():
    """Scrape Brackendale Art Gallery events."""
    events = []
    url = "https://brackendaleartgallery.com/whats-happening-at-the-bag/"
    page_html = fetch_url(url)
    if not page_html:
        return events
    
    # Similar approach - look for event data
    json_ld_pattern = r'<script type="application/ld\+json">([^<]+)</script>'
    json_matches = re.findall(json_ld_pattern, page_html)
    
    for json_str in json_matches:
        try:
            data = json.loads(json_str)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "Event":
                    start = item.get("startDate", "")
                    date_str = start[:10] if start else "TBD"
                    name = item.get("name", "Unknown Event")
                    if not should_exclude(name):
                        events.append({
                            "date": date_str,
                            "artist": html.unescape(name),
                            "venue": "Brackendale Art Gallery",
                            "source": "BAG"
                        })
        except json.JSONDecodeError:
            pass
    
    return events


# === Main ===

def collect_all_events():
    """Collect events from all sources."""
    all_events = []
    
    print("Scanning Songkick...", file=sys.stderr)
    songkick = scrape_songkick()
    print(f"  Found {len(songkick)} events", file=sys.stderr)
    all_events.extend(songkick)
    
    print("Scanning Trickster's Hideout...", file=sys.stderr)
    tricksters = scrape_eventbrite_tricksters()
    print(f"  Found {len(tricksters)} events", file=sys.stderr)
    all_events.extend(tricksters)
    
    print("Scanning The Backyard...", file=sys.stderr)
    backyard = scrape_backyard()
    print(f"  Found {len(backyard)} events", file=sys.stderr)
    all_events.extend(backyard)
    
    print("Scanning Brackendale Art Gallery...", file=sys.stderr)
    bag = scrape_brackendale()
    print(f"  Found {len(bag)} events", file=sys.stderr)
    all_events.extend(bag)
    
    spotify_profile = load_spotify_profile()
    related_index = load_related_artist_index()
    if spotify_profile:
        return enrich_events_with_preferences(all_events, spotify_profile, related_index=related_index)
    return all_events


def deduplicate_events(events):
    """Remove duplicate events based on date + artist + venue."""
    seen = set()
    unique = []
    for e in events:
        # Normalize for comparison
        artist_key = e.get("artist", "").lower().strip()
        venue_key = e.get("venue", "").lower().strip()
        date_key = e.get("date", "").lower().strip()
        
        key = (date_key, artist_key, venue_key)
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique


def parse_date_for_sort(date_str):
    """Parse date string for sorting."""
    parsed = parse_event_date(date_str)
    if parsed is None:
        return datetime.max  # Put unparseable dates at the end
    return datetime.combine(parsed, datetime.min.time())


def format_digest(events):
    """Format events as a Telegram-friendly markdown digest."""
    if not events:
        return "🎸 **Weekly Show Digest**\n\nNo shows found matching your criteria. Maybe check venue websites directly?"
    
    # Split into Vancouver and Squamish
    squamish_keywords = ["trickster", "backyard", "brackendale"]
    van_events = []
    sqm_events = []
    
    for e in events:
        venue_lower = e.get("venue", "").lower()
        if any(kw in venue_lower for kw in squamish_keywords):
            sqm_events.append(e)
        else:
            van_events.append(e)
    
    # Sort by date
    van_events.sort(key=lambda x: parse_date_for_sort(x.get("date", "")))
    sqm_events.sort(key=lambda x: parse_date_for_sort(x.get("date", "")))
    
    lines = ["🎸 **Weekly Show Digest**\n"]
    
    if van_events:
        lines.append("**Vancouver**")
        for e in van_events:
            date = e.get('date', 'TBD')
            artist = e.get('artist', 'TBD')
            venue = e.get('venue', 'TBD')
            lines.append(f"• {date} — **{artist}** @ {venue}")
        lines.append("")
    
    if sqm_events:
        lines.append("**Squamish**")
        for e in sqm_events:
            date = e.get('date', 'TBD')
            artist = e.get('artist', 'TBD')
            venue = e.get('venue', 'TBD')
            lines.append(f"• {date} — **{artist}** @ {venue}")
        lines.append("")
    
    lines.append(f"_Scanned {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    
    return "\n".join(lines)


def main():
    """Main entry point."""
    print("Starting show scan...", file=sys.stderr)
    
    events = collect_all_events()
    print(f"Found {len(events)} raw events", file=sys.stderr)
    
    events = deduplicate_events(events)
    print(f"After dedup: {len(events)} events", file=sys.stderr)
    events = filter_events_to_window(events)
    print(f"After date filter: {len(events)} events", file=sys.stderr)
    
    digest = format_digest(events)
    print(digest)


if __name__ == "__main__":
    main()
