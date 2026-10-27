# UI screenshots

Real screenshots refreshed on 27 October 2026 from the rebuilt frontend/Nginx and CPU backend containers on port 8081. Hand Test verification used an isolated Chromium browser through Playwright because the in-app automation connection was unavailable. Images show real uploads and actual D4 predictions; they are not generated mockups.

- `desktop-empty.jpg`: initial upload interface, retained accuracy table and computational metrics awaiting a run, 1280px viewport.
- `desktop-results.jpg`: actual D4 prediction, measured computational performance and download controls, 1280px viewport.
- `tablet-results.jpg`: actual results at a 768px viewport.
- `mobile-results.jpg`: stacked upload, results and performance at a 390px viewport.
- `hand-test-desktop.jpg`: side-by-side reference/prediction and actual full-image scores, 1280px viewport.
- `hand-test-tablet.jpg`: side-by-side comparison at a 768px viewport.
- `hand-test-mobile.jpg`: vertically stacked equal-square masks at a 390px viewport.

Original-tab screenshots use Bolivia_195474; Hand Test screenshots use India_900498. No sample is preloaded in the app's initial state. The historical table retains centre-crop scores. The comparison section contains separately calculated full-image scores for the uploaded reference.

The `docs/example-*.png` files are actual image outputs from the CPU Docker API, not UI screenshots.
