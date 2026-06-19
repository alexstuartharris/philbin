#!/usr/bin/env python3
"""
Build a reusable show-preference profile from a Spotify extended streaming history export.

This produces a compact JSON file the show scanner can use for direct artist matching
and "likely Alex show" flagging.
"""

from __future__ import annotations

import argparse
import glob
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
import re


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT_DIR / "apps/show-scanner/data/spotify_profile.json"


def normalize_artist_name(name: str) -> str:
    normalized = (name or "").strip().lower()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def artist_is_usable(name: str) -> bool:
    stripped = (name or "").strip()
    normalized = normalize_artist_name(stripped)
    if len(normalized) < 4:
        return False
    if stripped.isupper() and len(stripped) <= 4:
        return False
    return True


def build_profile(export_dir: Path, recent_year_cutoff: int = 2024, top_n: int = 250) -> dict:
    overall_plays = Counter()
    overall_ms = Counter()
    recent_plays = Counter()
    recent_ms = Counter()
    years_loaded = []
    total_rows = 0

    for path_str in sorted(glob.glob(str(export_dir / "Streaming_History_Audio_*.json"))):
        path = Path(path_str)
        year_match = re.search(r"(\d{4})", path.stem)
        year = int(year_match.group(1)) if year_match else None
        years_loaded.append(year)

        with path.open() as f:
            rows = json.load(f)

        for row in rows:
            artist = (row.get("master_metadata_album_artist_name") or "").strip()
            if not artist or not artist_is_usable(artist):
                total_rows += 1
                continue

            duration_ms = int(row.get("ms_played") or 0)
            overall_plays[artist] += 1
            overall_ms[artist] += duration_ms
            if year and year >= recent_year_cutoff:
                recent_plays[artist] += 1
                recent_ms[artist] += duration_ms
            total_rows += 1

    if not overall_plays:
        raise SystemExit("No usable artist history found in export")

    max_overall_plays = max(overall_plays.values())
    max_recent_plays = max(recent_plays.values()) if recent_plays else 1
    max_overall_ms = max(overall_ms.values())
    max_recent_ms = max(recent_ms.values()) if recent_ms else 1

    artists = []
    for artist, plays in overall_plays.most_common(top_n):
        hours = overall_ms[artist] / 3_600_000
        recent_play_count = recent_plays.get(artist, 0)
        recent_hours = recent_ms.get(artist, 0) / 3_600_000

        overall_component = (
            0.45 * (plays / max_overall_plays) +
            0.15 * (overall_ms[artist] / max_overall_ms)
        )
        recent_component = (
            0.25 * (recent_play_count / max_recent_plays) +
            0.15 * (recent_ms.get(artist, 0) / max_recent_ms)
        )
        weight = round((overall_component + recent_component) * 100, 2)

        artists.append({
            "artist": artist,
            "artist_normalized": normalize_artist_name(artist),
            "overall_plays": plays,
            "overall_hours": round(hours, 2),
            "recent_plays": recent_play_count,
            "recent_hours": round(recent_hours, 2),
            "weight": weight,
        })

    return {
        "generated": datetime.utcnow().isoformat() + "Z",
        "source": str(export_dir),
        "recent_year_cutoff": recent_year_cutoff,
        "rows_analyzed": total_rows,
        "years_loaded": sorted(y for y in years_loaded if y),
        "artist_count": len(artists),
        "artists": artists,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Spotify-derived taste profile for show scanner.")
    parser.add_argument("export_dir", help="Path to extracted 'Spotify Extended Streaming History' folder")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON path")
    parser.add_argument("--recent-year-cutoff", type=int, default=2024, help="Treat this year and later as recent listening")
    parser.add_argument("--top-n", type=int, default=250, help="Number of artists to retain in the profile")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    export_dir = Path(args.export_dir)
    output_path = Path(args.output)
    profile = build_profile(export_dir, recent_year_cutoff=args.recent_year_cutoff, top_n=args.top_n)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(profile, indent=2) + "\n")
    print(f"Wrote {output_path} with {profile['artist_count']} artists from {profile['rows_analyzed']} rows")


if __name__ == "__main__":
    main()
