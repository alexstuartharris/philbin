# Field Evidence Capture (v0)

Simple local-first prototype for field photo evidence records.

## Current features
- Photo capture/upload (`capture=environment`)
- Timestamped records (ISO + local time)
- GPS capture with accuracy
- Optional stamped copy (overlay text burned into image)
- SHA-256 hash for original/stamped image
- IndexedDB-backed storage (binary blobs, much larger capacity than localStorage)
- Legacy v0 localStorage migration on first load
- JSONL + CSV export
- ZIP export (metadata + images) when JSZip is available
- Per-record ZIP download
- PWA basics (manifest + service worker)
- Map preview of captured points (Leaflet)
- Basemap switcher: OpenStreetMap + Esri World Imagery (no API key)

## Known limitations
- ZIP export depends on JSZip CDN availability for full offline archive behavior
- No EXIF write-back/edit yet
- No signed chain-of-custody record
- No map preview yet

## Next steps
1. Add project templates (inspection/restoration/hydrology)
2. Add optional cloud sync (Convex/S3)
3. Add signed chain-of-custody export manifest
4. Add optional EXIF metadata helper (non-destructive)
5. Add GPX/KML export for GIS handoff
