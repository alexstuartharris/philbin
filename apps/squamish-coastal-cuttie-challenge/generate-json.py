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


def parse_ampm_time(raw: str):
    raw = raw.strip().lower().replace(" ", "")
    m = re.match(r"(\d{1,2}):(\d{2})(am|pm)", raw)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2))
    ampm = m.group(3)
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    return hour, minute


def parse_high_tides(html: str):
    timezone_match = re.search(r"Time\s*\(([^)]+)\)", html, re.I)
    tz_abbr = timezone_match.group(1) if timezone_match else ""

    day_header = re.compile(
        r"Tide Times for Squamish(?: \(tomorrow\))?:\s+([A-Za-z]+)\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
        re.I,
    )
    matches = list(day_header.finditer(html))
    tides = []
    daylight = {}

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        block = html[start:end]

        weekday_name = match.group(1)
        day = int(match.group(2))
        month_name = match.group(3)
        year = int(match.group(4))
        month = month_index.get(month_name)
        if not month:
            continue

        date_key = f"{year:04d}-{month:02d}-{day:02d}"

        tide_rows = re.finditer(r"<tr[^>]*>.*?<td>\s*(High Tide|Low Tide)\s*</td>.*?<td><b>\s*([0-9]{1,2}:[0-9]{2})\s*(AM|PM)\s*</b>", block, re.I | re.S)
        for row in tide_rows:
            kind = row.group(1).lower()
            if "high" not in kind:
                continue
            raw_time = f"{row.group(2)}{row.group(3)}"
            parsed = parse_ampm_time(raw_time)
            if not parsed:
                continue
            hour, raw_minute = parsed
            tides.append({
                "year": year,
                "month": month,
                "day": day,
                "hour": hour,
                "minute": raw_minute,
            })

        sunrise_match = re.search(r"Sunrise is at\s*([0-9: ]+[APMapm]{2})", block, re.I)
        sunset_match = re.search(r"sunset is at\s*([0-9: ]+[APMapm]{2})", block, re.I)
        sunrise = parse_ampm_time(sunrise_match.group(1)) if sunrise_match else None
        sunset = parse_ampm_time(sunset_match.group(1)) if sunset_match else None
        daylight[date_key] = {
            "weekdayName": weekday_name,
            "sunrise": sunrise,
            "sunset": sunset,
        }

    return tides, tz_abbr, daylight


def pretty_local(dt: datetime):
    month = dt.strftime("%b")
    weekday = dt.strftime("%a")
    day = dt.day
    hour = dt.strftime("%I").lstrip("0") or "0"
    minute = dt.strftime("%M")
    ampm = dt.strftime("%p")
    return f"{weekday}, {month} {day}, {hour}:{minute} {ampm}"


def build_windows(tides, tz_abbr, daylight):
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

        date_key = tide_local.strftime("%Y-%m-%d")
        day_info = daylight.get(date_key, {})
        sunrise = day_info.get("sunrise")
        sunset = day_info.get("sunset")
        is_weekend = window_start_local.weekday() >= 5

        if sunrise and sunset:
            fishable_start_minutes = sunrise[0] * 60 + sunrise[1] if is_weekend else WEEKDAY_AFTER_MINUTES
            fishable_end_minutes = sunset[0] * 60 + sunset[1]
            window_start_minutes = window_start_local.hour * 60 + window_start_local.minute
            window_end_minutes = window_end_local.hour * 60 + window_end_local.minute
            overlap_start = max(window_start_minutes, fishable_start_minutes)
            overlap_end = min(window_end_minutes, fishable_end_minutes)
            available = overlap_end > overlap_start
            if not available:
                if window_end_minutes <= fishable_start_minutes:
                    availability_note = "Before fishable hours"
                elif window_start_minutes >= fishable_end_minutes:
                    availability_note = "After sunset"
                else:
                    availability_note = "Outside daylight window"
            else:
                if is_weekend:
                    availability_note = f"Daylight window ({pretty_clock(*sunrise)}–{pretty_clock(*sunset)})"
                else:
                    availability_note = f"After work before sunset (5:30 PM–{pretty_clock(*sunset)})"
        else:
            start_minutes = window_start_local.hour * 60 + window_start_local.minute
            available = (is_weekend and 6 * 60 <= start_minutes <= 20 * 60) or (not is_weekend and WEEKDAY_AFTER_MINUTES <= start_minutes <= 20 * 60)
            availability_note = "Fallback daylight estimate"

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
            "Available windows are limited to daylight, and on weekdays they must also overlap 5:30 PM to sunset.",
        ],
    }


def pretty_clock(hour: int, minute: int):
    suffix = "AM"
    display_hour = hour
    if hour == 0:
        display_hour = 12
    elif hour == 12:
        suffix = "PM"
        display_hour = 12
    elif hour > 12:
        suffix = "PM"
        display_hour = hour - 12
    return f"{display_hour}:{minute:02d} {suffix}"


def main():
    html = fetch_html()
    tides, tz_abbr, daylight = parse_high_tides(html)
    if not tides:
        raise RuntimeError("No high tide entries parsed from source.")
    payload = build_windows(tides, tz_abbr, daylight)
    with open("data/tides.json", "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote data/tides.json with {len(payload['windows'])} windows")


if __name__ == "__main__":
    main()
