# sites/

Static sites deployed to Firebase Hosting (project `esh27-unicorn-core`).
One folder per site; the folder name is the hosting target in `firebase.json` / `.firebaserc`.

- Only folders that contain an `index.html` are deployed. Empty targets are skipped.
- Pull requests get a 7-day preview URL; pushes to `main` go live on `esh27-<name>.web.app`.
- Custom domains (`<name>.esh27.com`) are connected per site in the Firebase console,
  and DNS is moved one subdomain at a time. Until then Hostinger stays live and untouched.

`status/` is the pilot. The live content of the other sites is in `esh27-portal` (local) and is copied here per site.
