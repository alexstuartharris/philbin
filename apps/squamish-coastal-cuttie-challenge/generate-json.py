#!/usr/bin/env python3
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SOURCE_URL = "https://www.tide-forecast.com/locations/Squamish-British-Columbia/tides/latest"
TIME_ZONE = "America/Vancouver"
WEEKDAY_AFTER_MINUTES = 17 * 60 + 30

month_index = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


def fetch_html():
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def parse_high_tides(html: str):
    timezone_match = re.search(r"Time\s*\(([^)]+)\)", html, re.I)
    tz_abbr = timezone_match.group(1) if timezone_match else ""

    day_header = re.compile(
        r"Tide Times for Squamish(?: \(tomorrow\))?:\s+([A-Za-z]+)\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
        re.I,
    )
    matches = list(day_header.finditer(html))
    tides = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        block = html[start:end]

        day = int(match.group(2))
        month_name = match.group(3)
        year = int(match.group(4))
        month = month_index.get(month_name)
        if not month:
            continue

        tide_rows = re.finditer(r"<tr[^>]*>.*?<td>\s*(High Tide|Low Tide)\s*</td>.*?<td><b>\s*([0-9]{1,2}:[0-9]{2})\s*(AM|PM)\s*</b>", block, re.I | re.S)
        for row in tide_rows:
            kind = row.group(1).lower()
            if "high" not in kind:
                continue
            raw_time = row.group(2)
            ampm = row.group(3).upper()
            raw_hour, raw_minute = [int(x) for x in raw_time.split(":")]
            hour = raw_hour
            if ampm == "PM" and hour < 12:
                hour += 12
            if ampm == "AM" and hour == 12:
                hour = 0
            tides.append({
                "year": year,
                "month": month,
                "day": day,
                "hour": hour,
                "minute": raw_minute,
            })

    return tides, tz_abbr


def pretty_local(dt: datetime):
    month = dt.strftime("%b")
    weekday = dt.strftime("%a")
    day = dt.day
    hour = dt.strftime("%I").lstrip("0") or "0"
    minute = dt.strftime("%M")
    ampm = dt.strftime("%p")
    return f"{weekday}, {month} {day}, {hour}:{minute} {ampm}"


def build_windows(tides, tz_abbr):
    tz = ZoneInfo(TIME_ZONE)
    windows = []
    for tide in tides:
        tide_local = datetime(
            tide["year"], tide["month"], tide["day"], tide["hour"], tide["minute"], tzinfo=tz
        )
        tide_utc = tide_local.astimezone(timezone.utc)
        window_start_local = tide_local - timedelta(hours=1)
        window_end_local = tide_local + timedelta(hours=1)
        window_start_utc = tide_utc - timedelta(hours=1)
        window_end_utc = tide_utc + timedelta(hours=1)

        is_weekend = window_start_local.weekday() >= 5
        start_minutes = window_start_local.hour * 60 + window_start_local.minute
        available = is_weekend or start_minutes >= WEEKDAY_AFTER_MINUTES
        availability_note = (
            "Weekend availability"
            if is_weekend
            else "Weekday after 5:30 PM"
            if available
            else "Weekday before 5:30 PM"
        )

        windows.append({
            "dateLocal": window_start_local.strftime("%Y-%m-%d"),
            "highTideLocal": pretty_local(tide_local),
            "windowStartLocal": pretty_local(window_start_local),
            "windowEndLocal": pretty_local(window_end_local),
            "windowStartUtc": window_start_utc.isoformat().replace("+00:00", "Z"),
            "windowEndUtc": window_end_utc.isoformat().replace("+00:00", "Z"),
            "available": available,
            "availabilityNote": availability_note,
        })

    windows.sort(key=lambda x: x["windowStartUtc"])
    now = datetime.now(tz)
    return {
        "source": SOURCE_URL,
        "timeZone": TIME_ZONE,
        "timeZoneAbbr": tz_abbr,
        "fetchedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "nowLocalDate": now.strftime("%Y-%m-%d"),
        "windows": windows,
        "notes": [
            "Tide data is scraped from tide-forecast.com HTML and may change without notice.",
            "Windows are computed as +/- 1 hour around high tide; verify timing before planning a trip.",
            "Availability is marked as weekends or weekdays after 5:30 PM.",
        ],
    }


def main():
    html = fetch_html()
    tides, tz_abbr = parse_high_tides(html)
    if not tides:
        raise RuntimeError("No high tide entries parsed from source.")
    payload = build_windows(tides, tz_abbr)
    with open("data/tides.json", "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote data/tides.json with {len(payload['windows'])} windows")


if __name__ == "__main__":
    main()
