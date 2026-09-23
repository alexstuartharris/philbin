# Philbin Apps

A collection of small web apps and workflow tools published through GitHub Pages.

- **Live app directory:** https://alexstuartharris.github.io/philbin/
- **Browse app source:** https://github.com/alexstuartharris/philbin/tree/main/apps

## Repository layout

| Path | Purpose |
| --- | --- |
| `apps/` | Source for every deployed web app |
| `.github/workflows/pages.yml` | Builds and deploys GitHub Pages |
| `scripts/generate-manifest.mjs` | Generates the deployed app inventory |
| `docs/` | Project notes and historical documentation |

## Deployment model

GitHub Pages uploads the contents of `apps/` as the website root. For example:

- `apps/show-scanner/` is published at `/show-scanner/`
- `apps/squamish-coastal-cuttie-challenge/` is published at `/squamish-coastal-cuttie-challenge/`

The deployment workflow generates `apps/manifest.json` during CI. That generated file is intentionally not tracked in Git.
