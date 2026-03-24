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
import re
import sys
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError


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
    "malkin-bowl": "Malkin Bowl",
    "hollywood-theatre": "Hollywood Theatre",
    "fortune-sound-club": "Fortune Sound Club",
    "the-pearl": "The Pearl",
    "queen-elizabeth-theatre": "Queen Elizabeth Theatre",
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

WEEKS_AHEAD = 3


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
    except URLError as e:
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


# === Scrapers ===

def scrape_songkick():
    """Scrape Songkick Vancouver metro for upcoming shows at target venues."""
    events = []
    base_url = "https://www.songkick.com/metro-areas/27398-canada-vancouver"
    
    for page in range(1, 15):  # First 14 pages (covers ~9 months)
        url = f"{base_url}?page={page}" if page > 1 else base_url
        page_html = fetch_url(url)
        if not page_html:
            continue
        
        # Track current date from HTML structure
        current_date = None
        
        # Find date headers
        date_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d+)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})'
        
        # Build a map of concert IDs to their full lineup from multiple sources
        artist_map = {}
        
        # Source 1: alt attributes on artist images (most reliable for full lineup + date)
        # Pattern: alt="Chiodos, sace6, and 156/Silence at Commodore Ballroom (07 Aug 26)"
        alt_pattern = r'alt="([^"]+)\s+at\s+([^"(]+)\s*\((\d+)\s+(\w+)\s+(\d+)\)"'
        
        # Month abbreviation to full name mapping
        month_map = {
            "jan": "January", "feb": "February", "mar": "March", "apr": "April",
            "may": "May", "jun": "June", "jul": "July", "aug": "August",
            "sep": "September", "oct": "October", "nov": "November", "dec": "December"
        }
        
        for match in re.finditer(alt_pattern, page_html):
            lineup = html.unescape(match.group(1).strip())
            venue_raw = match.group(2).strip()
            day = match.group(3)
            month_abbr = match.group(4)
            year = match.group(5)
            
            # Convert month abbreviation to full name
            month_full = month_map.get(month_abbr.lower()[:3], month_abbr)
            
            # Convert venue name to slug for matching
            venue_slug = venue_raw.lower().replace(' ', '-').replace("'", "")
            venue_name = venue_matches(venue_slug)
            
            # Also try direct name matching
            if not venue_name:
                for slug, name in {**VANCOUVER_VENUES, **SQUAMISH_VENUES}.items():
                    if name.lower() in venue_raw.lower() or venue_raw.lower() in name.lower():
                        venue_name = name
                        break
            
            if venue_name and not should_exclude(lineup):
                # Build a key based on lineup + venue for later matching
                key = (lineup.lower(), venue_name.lower())
                artist_map[key] = {
                    "lineup": lineup,
                    "venue": venue_name,
                    "date_hint": f"{month_full} {day}, 20{year}"
                }
        
        # Source 2: <strong> tags in event links (fallback)
        # Pattern: <a class="event-link" href="/concerts/43062105-avro-at-green-auto">
        #            <span><strong>Avro, DIELECTRIC, EARS (BC), and Wack</strong></span>
        concert_map = {}
        event_link_pattern = r'<a[^>]*href="/concerts/(\d+)-[^"]+at-([^"]+)"[^>]*>\s*(?:<span>)?\s*<strong>([^<]+)</strong>'
        for match in re.finditer(event_link_pattern, page_html, re.IGNORECASE | re.DOTALL):
            concert_id = match.group(1)
            venue_slug = match.group(2).lower()
            full_lineup = html.unescape(match.group(3).strip())
            concert_map[concert_id] = {
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
            link_match = re.search(r'/concerts/(\d+)-([a-z0-9-]+)-at-([a-z0-9-]+)', line.lower())
            if link_match and current_date:
                concert_id = link_match.group(1)
                artist_slug = link_match.group(2)
                venue_slug = link_match.group(3)
                
                # Check if venue matches our list
                venue_name = venue_matches(venue_slug)
                if venue_name:
                    artist_name = None
                    event_date = current_date  # Default to section date
                    
                    # Try concert_map first (from <strong> tags)
                    if concert_id in concert_map:
                        artist_name = concert_map[concert_id]["lineup"]
                    
                    # Check if we have a better lineup AND date from alt attributes
                    # Match by checking if artist_slug is in any alt-derived lineup
                    headliner_clean = clean_artist_name(artist_slug).lower()
                    for key, data in artist_map.items():
                        lineup_lower, venue_lower = key
                        if headliner_clean in lineup_lower and venue_name.lower() == venue_lower:
                            artist_name = data["lineup"]
                            # Use the date from alt attribute (more accurate)
                            if data.get("date_hint"):
                                event_date = data["date_hint"]
                            break
                    
                    # Fallback to URL slug
                    if not artist_name:
                        artist_name = clean_artist_name(artist_slug)
                    
                    # Skip if excluded genre/style
                    if should_exclude(artist_name):
                        continue
                    
                    events.append({
                        "date": event_date,
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


# Do604 venue slugs to scrape
DO604_VENUES = {
    "green-auto": "Green Auto",
    "fox-cabaret": "Fox Cabaret",
    "biltmore-cabaret": "Biltmore Cabaret",
    "rickshaw-theatre": "Rickshaw Theatre",
    "the-cobalt": "The Cobalt",
    "lanalous": "Lanalou's",
    "hollywood-theatre": "Hollywood Theatre",
    "fortune-sound-club": "Fortune Sound Club",
    "the-pearl-on-granville": "The Pearl",
}


def scrape_do604():
    """Scrape Do604 venue pages for local shows."""
    events = []
    
    for venue_slug, venue_name in DO604_VENUES.items():
        url = f"https://do604.com/venues/{venue_slug}.json"
        json_str = fetch_url(url)
        if not json_str:
            continue
        
        try:
            data = json.loads(json_str)
            event_groups = data.get("event_groups", [])
            
            for group in event_groups:
                date_str = group.get("date", "")
                
                for event in group.get("events", []):
                    title = event.get("title", "")
                    if not title or should_exclude(title):
                        continue
                    
                    # Parse date to consistent format
                    try:
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_date = dt.strftime("%B %d, %Y")
                    except ValueError:
                        formatted_date = date_str
                    
                    event_id = event.get("id", "")
                    permalink = event.get("permalink", "")
                    
                    events.append({
                        "date": formatted_date,
                        "artist": html.unescape(title),
                        "venue": venue_name,
                        "link": f"https://do604.com{permalink}" if permalink else "",
                        "source": "Do604",
                        "_id": str(event_id)  # For internal dedup
                    })
        except json.JSONDecodeError:
            continue
    
    return events


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
    
    print("Scanning Do604...", file=sys.stderr)
    do604 = scrape_do604()
    print(f"  Found {len(do604)} events", file=sys.stderr)
    all_events.extend(do604)
    
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
    
    return all_events


def extract_artists(artist_str):
    """Extract all artist names from a lineup string, normalized."""
    artist_str = artist_str.strip().lower()
    
    # Replace various separators with comma
    for sep in [" and ", " & ", " with ", " + ", " / ", " x "]:
        artist_str = artist_str.replace(sep, ", ")
    
    # Split and clean
    artists = [a.strip() for a in artist_str.split(",") if a.strip()]
    
    # Further normalize: remove parentheticals like "(BC)", common prefixes
    normalized = []
    for a in artists:
        # Remove parentheticals
        a = re.sub(r'\s*\([^)]*\)', '', a).strip()
        # Remove "the " prefix for matching
        if a.startswith("the "):
            a = a[4:]
        if a:
            normalized.append(a)
    
    return set(normalized)


def events_are_same_show(e1, e2):
    """Check if two events are the same show (same date, venue, overlapping artists)."""
    # Must be same date
    if e1.get("date", "").lower() != e2.get("date", "").lower():
        return False
    
    # Must be same venue (normalized)
    v1 = e1.get("venue", "").lower().replace("the ", "").replace("'", "").strip()
    v2 = e2.get("venue", "").lower().replace("the ", "").replace("'", "").strip()
    if v1 != v2:
        return False
    
    # Check for overlapping artists (at least 1 in common = same show)
    artists1 = extract_artists(e1.get("artist", ""))
    artists2 = extract_artists(e2.get("artist", ""))
    
    return bool(artists1 & artists2)


def count_artists(artist_str):
    """Count the number of artists in a lineup string."""
    return len(extract_artists(artist_str))


def deduplicate_events(events):
    """Remove duplicate events using artist overlap detection.
    
    Two events are duplicates if they share date, venue, and at least
    one artist in common. Prefers the entry with MORE artists listed
    (more complete lineup). If tied, prefers Songkick over Do604.
    """
    # Group duplicates together first
    groups = []
    used = set()
    
    for i, e in enumerate(events):
        if i in used:
            continue
        
        group = [e]
        used.add(i)
        
        # Find all duplicates of this event
        for j, other in enumerate(events):
            if j in used:
                continue
            if events_are_same_show(e, other):
                group.append(other)
                used.add(j)
        
        groups.append(group)
    
    # Pick best entry from each group
    # Priority: most artists listed, then source priority as tiebreaker
    source_priority = {"Songkick": 0, "Do604": 1, "Eventbrite": 2, "Backyard Squamish": 3, "BAG": 4}
    
    unique = []
    for group in groups:
        # Sort by: 1) artist count (descending), 2) source priority (ascending)
        group.sort(key=lambda x: (
            -count_artists(x.get("artist", "")),  # More artists = better (negative for descending)
            source_priority.get(x.get("source", ""), 99)
        ))
        unique.append(group[0])
    
    return unique


def parse_date_for_sort(date_str):
    """Parse date string for sorting."""
    formats = [
        "%B %d, %Y",  # March 23, 2026
        "%Y-%m-%d",   # 2026-03-23
        "%b %d, %Y",  # Mar 23, 2026
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return datetime.max  # Put unparseable dates at the end


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
    
    digest = format_digest(events)
    print(digest)


if __name__ == "__main__":
    main()
