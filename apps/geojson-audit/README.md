# GeoJSON Audit

A tiny, static, GitHub Pages–friendly tool to:
- validate GeoJSON (parse + basic type checks)
- preview it on a map (Leaflet)
- compute quick QA stats (Turf): feature counts, bbox, property keys, approx area/length

## Run locally

Just open `index.html` in a browser.

## Notes

- Leaflet expects WGS84 (EPSG:4326 lon/lat). If your data is projected, reproject first.
- Area/length are *approximate* (useful for QA, not survey-grade).
