# Nightly Builds Log

This repo is Philbin's playground for small web apps and workflow tools.

## How to run things
- Each project should include its own README with exact commands.
- For web apps intended for GitHub Pages, put the deployable static build output under `apps/<name>/dist` (or document the build step), and update the Pages workflow if needed.

## Rehearsal tools
- Daily standup helper in `tools/daily-standup/` writes a dated markdown log after three prompts.
- Test it with `node tools/daily-standup/standup.js` and confirm a new file appears under `tools/daily-standup/logs/`.

## Nightly routine
- A nightly branch + PR is created around 10:30pm (America/Vancouver).
- Each PR includes:
  - what was built
  - how to test
  - next possible improvements
