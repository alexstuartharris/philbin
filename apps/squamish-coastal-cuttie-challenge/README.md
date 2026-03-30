# Squamish Coastal Cuttie Challenge

A lightweight static tide-window viewer for Squamish, BC.

## What it does
- Fetches tide data from tide-forecast.com
- Parses upcoming high tides for Squamish
- Computes fishing windows as **1 hour before to 1 hour after high tide**
- Flags windows as:
  - **Available** on weekends
  - **Available** on weekdays after **5:30 PM**
  - **Unavailable** otherwise

## Notes
This is a standalone static extraction of the original Squamish fishing/tide tool logic that was previously living inside the Task Board app.

## Caveat
Because this is a pure static app running in-browser, it depends on the source site allowing direct fetches from GitHub Pages. If the upstream site blocks cross-origin requests, the app may need a proxy or pre-generated data step later.
