# utm-buddy

Convert coordinates between **WGS84 Lat/Lon** and **UTM** in the browser.

- Works as a static site (GitHub Pages-friendly)
- No API keys
- Runs entirely client-side

## Use

Open:
- `apps/utm-buddy/index.html` locally, or
- https://alexstuartharris.github.io/philbin/apps/utm-buddy/

### Convert Lat/Lon → UTM
1. Select **Lat/Lon → UTM**
2. Choose **UTM zone** (1–60) + hemisphere
3. Paste or upload CSV data containing lat/lon columns
4. Pick the **Latitude** and **Longitude** columns
5. Click **Convert** then **Download CSV**

### Convert UTM → Lat/Lon
1. Select **UTM → Lat/Lon**
2. Choose **UTM zone** + hemisphere
3. Paste or upload CSV data containing easting/northing columns
4. Pick the **Easting** and **Northing** columns
5. Click **Convert** then **Download CSV**

## Notes
- Assumes **WGS84** for both Lat/Lon and UTM.
- Output adds new columns; original columns are preserved.

## Next improvements
- Auto-detect UTM zone from lon
- Support NAD83 / custom datum via proj definitions
- Map preview / validation (range checks, outliers)
