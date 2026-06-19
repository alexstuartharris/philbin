#!/usr/bin/env python3
"""
Build a related-artist cache for the show scanner from the Spotify taste profile.

Uses public Last.fm similar-artist pages as a lightweight discovery layer.
This is intentionally cached to a local JSON file so the daily scanner does not
depend on extra network lookups for every run.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, unquote_plus
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT_DIR / "apps/show-scanner/data/spotify_profile.json"
DEFAULT_OUTPUT = ROOT_DIR / "apps/show-scanner/data/spotify_related_artists.json"


def normalize_artist_name(name: str) -> str:
    normalized = (name or "").strip().lower()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def fetch_url(url: str, timeout: int = 20) -> str | None:
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    try:
        with urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def extract_similar_artists(html_text: str, seed_artist: str, limit: int = 15) -> list[dict]:
    seed_norm = normalize_artist_name(seed_artist)
    hrefs = re.findall(r'href="/music/([^"/][^"]+?)"', html_text)
    results = []
    seen = set()

    for raw in hrefs:
        if raw.endswith("/+wiki") or raw.endswith("/+events") or raw.endswith("/+tracks") or raw.endswith("/+albums") or raw.endswith("/+similar"):
            continue
        if "/+" in raw:
            continue

        artist = unquote_plus(raw).strip()
        artist = artist.replace("_", " ")
        normalized = normalize_artist_name(artist)
        if not normalized or normalized == seed_norm or normalized in seen:
            continue

        # Keep obvious artist-like strings only.
        if len(normalized) < 4:
            continue

        seen.add(normalized)
        results.append({
            "artist": artist,
            "artist_normalized": normalized,
            "rank": len(results) + 1,
        })
        if len(results) >= limit:
            break

    return results


def build_similarity_cache(profile_path: Path, output_path: Path, seed_count: int = 40, similar_limit: int = 15, delay_s: float = 0.4) -> dict:
    profile = json.loads(profile_path.read_text())
    seed_artists = profile.get("artists", [])[:seed_count]
    index: dict[str, list[dict]] = {}
    seeds_output = []

    for idx, seed in enumerate(seed_artists, start=1):
        artist = seed["artist"]
        url = f"https://www.last.fm/music/{quote_plus(artist)}/+similar"
        html_text = fetch_url(url)
        similar_artists = extract_similar_artists(html_text or "", artist, limit=similar_limit)

        seed_entry = {
            "seed_artist": artist,
            "seed_artist_normalized": seed["artist_normalized"],
            "seed_weight": seed["weight"],
            "source_url": url,
            "similar_artists": similar_artists,
        }
        seeds_output.append(seed_entry)

        for item in similar_artists:
            related_score = round(max(10.0, 55 - ((item["rank"] - 1) * 2.0) + (seed["weight"] * 0.15)), 2)
            index.setdefault(item["artist_normalized"], []).append({
                "artist": item["artist"],
                "seed_artist": artist,
                "seed_weight": seed["weight"],
                "rank": item["rank"],
                "related_score": related_score,
                "source": "lastfm_similar",
            })

        if idx < len(seed_artists):
            time.sleep(delay_s)

    for values in index.values():
        values.sort(key=lambda item: (-item["related_score"], item["rank"], item["seed_artist"].lower()))

    output = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "source_profile": str(profile_path),
        "seed_count": len(seed_artists),
        "similar_limit": similar_limit,
        "related_artist_count": len(index),
        "seeds": seeds_output,
        "related_index": index,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build related-artist cache for the show scanner.")
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE), help="Path to spotify_profile.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output path")
    parser.add_argument("--seed-count", type=int, default=40, help="Number of top Spotify artists to use as seeds")
    parser.add_argument("--similar-limit", type=int, default=15, help="Number of similar artists to keep per seed")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = build_similarity_cache(
        profile_path=Path(args.profile),
        output_path=Path(args.output),
        seed_count=args.seed_count,
        similar_limit=args.similar_limit,
    )
    print(
        f"Wrote {args.output} with {output['related_artist_count']} related artists "
        f"from {output['seed_count']} seeds"
    )


if __name__ == "__main__":
    main()
