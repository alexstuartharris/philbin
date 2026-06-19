#!/usr/bin/env python3
"""
Convert scanner output to JSON for the web app.
Reads from scanner.py's output and generates events.json
"""

import json
import sys
from datetime import datetime
from scanner import collect_all_events, deduplicate_events, filter_events_to_window


def main():
    """Generate JSON output for the web app."""
    print("Collecting events...", file=sys.stderr)
    events = collect_all_events()
    
    print(f"Found {len(events)} raw events", file=sys.stderr)
    events = deduplicate_events(events)
    print(f"After dedup: {len(events)} events", file=sys.stderr)
    events = filter_events_to_window(events)
    print(f"After date filter: {len(events)} events", file=sys.stderr)
    
    # Prepare output
    output = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "count": len(events),
        "events": events
    }
    
    # Write to data/events.json
    with open("data/events.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"✓ Generated data/events.json with {len(events)} events", file=sys.stderr)


if __name__ == "__main__":
    main()
