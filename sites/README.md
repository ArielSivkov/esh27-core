# sites/

Static sites. One folder per site; the folder name is the site name (`<name>.esh27.com`).

- **Cloudflare Pages (chosen 30.10.2026):** `.github/workflows/deploy-pages.yml` deploys every folder that has an
  `index.html` to the Pages project `esh27-<name>` (`esh27-<name>.pages.dev`). Steps, DNS and mail: `CLOUDFLARE_MIGRATION.md`.
- `scripts/import-hostinger-backup.sh <backup_dir>` copies the live sites from the Hostinger backup into these folders
  (static files only; PHP and secrets stay out).
- Earlier draft: Firebase Hosting (`firebase.json`, `.firebaserc`, `deploy-hosting.yml`). Remove it before merging if Cloudflare stays the choice.

`status/` is the pilot.
