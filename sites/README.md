# sites/

Static sites. One folder per site; the folder name is the site name (`<name>.esh27.com`).

- **Cloudflare Pages (chosen 30.10.2026):** `.github/workflows/deploy-pages.yml` deploys every folder that has an
  `index.html` to the Pages project `esh27-<name>` (`esh27-<name>.pages.dev`). Steps, DNS and mail: `CLOUDFLARE_MIGRATION.md`.
- `portal/` is the static front of esh27.com (Pages project `esh27-portal`).
- `scripts/import-hostinger-backup.sh <backup_dir>` copies the live sites from the Hostinger backup into these folders
  (static files only; PHP and secrets stay out).
- The earlier Firebase Hosting draft was removed on 30.10.2026 when Cloudflare was chosen.

`status/` is the pilot.
