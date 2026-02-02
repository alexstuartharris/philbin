# GeoJSON Metrics

Small client-side utility to compute quick metrics from GeoJSON:
- Feature count + geometry-type breakdown
- Total line length (m / km)
- Total polygon area (m² / ha)
- BBox + centroid
- Per-feature CSV export (flattens properties)

## Notes
- Runs entirely in the browser (no uploads).
- Uses Turf.js (geodesic calculations).

## Local test
From repo root:

```bash
python3 -m http.server 8080
```

Then open:
- http://localhost:8080/apps/geojson-metrics/
