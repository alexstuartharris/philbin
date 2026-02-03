# Checklist Buddy

A fast, offline-friendly checklist builder (site visits / QA / packing lists) that lives entirely in the browser.

- **No backend** / GitHub Pages friendly
- Stores state in `localStorage`
- Notes per item
- Export: **Markdown**, **CSV**, **JSON**
- Import: **JSON**
- Print-friendly

## Use

Open the deployed app via the Philbin index page:

- https://alexstuartharris.github.io/philbin/

Then select **checklist-buddy**.

## Local dev

Just open `apps/checklist-buddy/index.html` in a browser.

## Data format (JSON)

Exports look like:

```json
{
  "version": 1,
  "name": "My checklist",
  "updatedAt": "2026-02-03T06:30:00.000Z",
  "sections": [
    {
      "title": "Safety",
      "items": [
        { "text": "First aid kit", "done": false, "note": "" }
      ]
    }
  ]
}
```

(IDs and timestamps are included in the real export.)
