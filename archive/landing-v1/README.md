# Old Nifraim landing page (v1) — archived 2026-10-03

Replaced by `frontend/src/views/HomeView.vue` (lighthouse hero, Nifra Agent / Calls / Report / portal chapters, Kling videos).
These files are NOT built or deployed (`archive/` is in `.railwayignore`, outside `frontend/src`).

To restore: copy `LandingView.vue` back to `frontend/src/views/`, the `components/*` back to
`frontend/src/components/landing/`, and point the `/` route in `frontend/src/router/index.js` at it.
It still needs the public images under `frontend/public/images/landing/` (left in place).
