# Verification record

## JRC water separation, 29 October 2026

See [WATER_SEPARATION_VERIFICATION.md](WATER_SEPARATION_VERIFICATION.md) for the
current feature's 52 backend tests, 12 frontend tests, production build,
both-workspace browser checks, real downloads and all-ten-demo API verification.
This feature was tested using local Uvicorn/Vite because Docker was not running.
Docker evidence below applies to the earlier revisions identified there.

## Computational-only sidebar, 27 October 2026

Removed the sidebar's historical accuracy table, model subtitle, duplicate computational subheading and small resolution/timing explanation. It now contains one **Model computational performance** heading and Parameters, Device, Inference and Processing values. Header, comparison caption, image alt text and browser title use **DeepLab** instead of D4. Hand Test comparison scores, upload requirements and result controls remain unchanged. Model identity and historical scores are still retained in scientific metadata and documentation.

The 12 frontend tests and production build passed, and the actual frontend/Nginx container was rebuilt and recreated on port 8081. Browser regression checks verified the new heading, absent table/notes, DeepLab title/labels, both original workflows, current Hand Test scores, downloads, opacity, clear/re-upload, errors, recovery, keyboard navigation and 320/390/768/1280px layouts. Screenshots were refreshed and visually inspected. No backend, model or dataset files were changed, so the previously passing 38 Python tests were not repeated for this presentation-only edit. Antislop Delivery Gate remains PASS.

## Hand Test comparison, 27 October 2026

Branch: `hand-test-data`, based on `ui-enhancement`. The original Segmentation tab, background, checkpoint, normalization, four-patch inference, threshold and historical metrics are preserved. Only separate reference-validation/comparison behavior and the requested workspace tab were added.

### Automated and deployed checks

- **38 Python tests passed**, including all original checks and the host CUDA-agreement test. New tests cover known confusion counts, perfect/incorrect/no-water/no-valid-pixel metrics, JSON null scores, ignored -1/255 labels, nodata=0 background handling, sensor-invalid pixels, file limits, incorrect bands/dimensions/CRS/alignment, corrupt and mismatched labels, missing/duplicate/extra uploads and unavailable-model handling.
- **12 frontend tests passed**, including pair/triplet recognition, metadata filtering, missing labels, duplicate/extra files, identity/subfolder mismatches, oversized/empty ground truth and preservation of the original two-file rule.
- All ten triplets passed preview/prediction and independent metric recomputation. A changed ground-truth mask changed evaluation but left the exported prediction GeoTIFF byte-identical to both the original-reference result and the ordinary two-file endpoint's result.
- The Vite production build and standard source-based `docker compose up -d --build` completed successfully. Both containers were recreated on port 8081, and the backend became healthy. The final frontend was rebuilt once more after making the global tab lock update before paint.
- `scripts/check_deployment.py` checked served HTML/JavaScript/CSS byte-for-byte against the final local production build, the original background hash, original model metadata and all ten triplets through actual Nginx routes. Scores were independently recomputed from decoded GeoTIFF predictions and original labels.
- The backend container contains exactly **30 Hand Test TIFFs**; every bundled file's hash matches its manifest. The source split was verified during packaging: all ten are in Hand Test, none in training/validation. Copies total approximately 37.4 MiB and preserve original filenames and bytes.
- PNG downloads from both modes were inspected as 512 × 512 images; GeoTIFF downloads preserve EPSG:4326, 512 × 512 dimensions and nodata=255. All ten API-exported masks retain the source grid.

Pytest reports one existing Starlette/httpx deprecation warning. This did not fail any test. The deployed Docker service uses CPU. Host CUDA agreement passed; the updated GPU Docker override was not separately rebuilt or run for this addition.

### Actual browser interactions

The in-app automation connection returned no available browser. `scripts/check_ui.cjs` used an isolated headless Chromium browser through the bundled Playwright runtime against the running Docker app, not a mocked frontend. Intentional offline and corrupt-input cases were tested separately from normal success flows.

| Control / state | Observed result |
| --- | --- |
| Default Segmentation | Two-file folder selection, optical preview and real 512 × 512 prediction worked; response has no evaluation extension |
| Keyboard entry | First Tab showed the 3px green skip-link outline; Enter focused workspace |
| Hand Test tab | ArrowRight selected the new tab and retained original results in the hidden panel |
| Three-file selection | All filenames displayed; ground truth appeared beside an empty prediction placeholder before inference |
| Segment / Segment again | Both completed actual D4 inference and selected Compare |
| Processing lock | A controlled test delay before forwarding the real prediction request confirmed both tabs disabled and aria-busy=true |
| Compare | Ground truth and prediction used equal square frames and the same white/black/grey legend |
| Scores | Visible numbers matched the API: India_900498 IoU 91.47%, Dice 95.54%, pixel accuracy 95.82%; 261,992 evaluated and 152 excluded pixels |
| Optical / Radar / Mask / Overlay | Each worked with keyboard Space in both modes; Radar/Overlay also worked in the original tab at tablet/mobile widths |
| Opacity | Keyboard Home/End set 0%/100%; PageUp restored 50%; actual layer opacity was 0.5 |
| Downloads | Mask PNG, current-overlay PNG and mask GeoTIFF completed in both modes and were saved to ignored test artifacts |
| Tab preservation | Switching back restored Bolivia results; returning restored Hand Test comparison; arrow and End navigation worked |
| Clear / re-upload | Another triplet removed stale scores; Clear removed images/exports and restored Awaiting run timings |
| Missing/corrupt label | Correct frontend/server errors displayed; segmentation disabled for invalid input; Clear recovered |
| Service error / Retry | Simulated failed model-info network request showed Unavailable facts; removing the failure and Retry restored real model information |
| Diagnostics | No uncaught page errors in the complete interaction run |

At 1280/768px comparison masks were side by side; at 390/320px they stacked. Client width equalled scroll width at every tested width. All visible enabled buttons measured at least 44px high. Both tabs were checked on desktop, tablet and mobile. Seven real screenshots were saved and visually inspected. The final screenshot set contains no generated UI mockups.

### Design gate and interpretation

Antislop Delivery Gate: **PASS**, with rule-by-rule evidence in `ANTISLOP_GATE.md`. The retained palette/overlay has previously verified conservative contrast bounds: header green 4.59:1 over the brightest possible backdrop, muted panel text 8.41:1 and primary-button text 12.50:1. New comparison labels and metrics reuse these colours. Blur remains limited to the two visible upload/results panels.

The example scores above are full-image comparisons for one visually selected demonstration. They are not an aggregate score for the ten selected tiles or all 90 Hand Test tiles, and do not replace the historical centre-crop metrics. Reference masks may include permanent water.

## Neon dashboard revision, 27 October 2026

Scope: frontend appearance and a read-only computational-performance display. Backend logic, prediction behavior, saved model, sample files and the existing background image were not changed. Branch: `ui-enhancement`.

Seven frontend tests and the Vite production build passed. The final production CSS was tested through Vite preview on `http://localhost:8081/#workspace`, proxying the unchanged Python backend on port 8000 with CPU selected for this session.

Docker verification limitation: Docker Desktop was stopped and failed to start because its internal secrets-engine socket could not be accessed. The frontend container rebuild could not run. No factory reset, socket deletion or Docker configuration change was attempted. The original container verification below is historical evidence, not a claim that this revision was container-tested.

| Control / state | Current revision evidence |
| --- | --- |
| Empty / connecting | Observed loading model state, then CPU, exact parameter count, disabled inference and `Awaiting run` timings |
| Folder chooser | Enter opened the directory chooser; selecting `bolivia 3` validated both original TIFFs and showed Optical preview |
| Segment image / Segment again | Both completed real 512 × 512 predictions; processing `aria-busy=true` observed, Results received focus |
| Computational performance | API supplied 4,390,257 parameters and CPU. Captured run: 105.6 ms inference, 228.6 ms processing, four patches. Values vary per request; no FPS/VRAM/FLOPs claims |
| Optical / Radar / Mask / Overlay | Each keyboard Space activation changed the selected state and corresponding image alt text; mobile Radar and Overlay clicks also worked |
| Opacity | Home and End produced 0% and 100%; five PageUp presses restored 50%, and the actual overlay style was `opacity: 0.5` |
| Mask PNG | Actual download event completed; Pillow verified 512 × 512, grayscale |
| Overlay PNG | Actual download event completed at 50% opacity; Pillow verified 512 × 512, RGBA |
| Mask GeoTIFF | Actual download event completed; Rasterio verified 512 × 512, EPSG:4326, nodata=255 |
| Clear / re-upload | Clear removed images and exports, returned timings to `Awaiting run`, and allowed another folder selection |
| Missing partner | Neutral one-pair validation message displayed with the new amber error treatment |
| Corrupt pair | Decoder error displayed and segmentation remained disabled; Clear recovered |
| Service offline / retry | Stopping only the test backend showed the actionable service error and `Unavailable` model facts; restarting it and Retry connection restored facts and metrics |
| Keyboard | Tab exposed the skip link, Enter focused workspace, next Tab reached chooser; Enter chooser, Space views/prediction, range Home/End/PageUp and Shift+Tab back to Overlay all worked |
| Diagnostics | Fresh final reload reported no warnings or errors. Expected 422 and offline errors were checked separately |

Responsive checks: 1280, 768, 390 and 320px. Measured client/scroll widths were respectively 1265/1265, 753/753, 375/375 and 305/305 with scrollbars. No horizontal overflow. All enabled buttons were 44px or 46px high. Actual green keyboard outline was 3px solid. Mobile stacks upload, results, then performance. Square imagery remains unrotated and unresized by inference.

The production build initially dropped the standard backdrop-filter declaration when the vendor-prefixed property followed it. Reordering these declarations fixed the production output. Computed styles then verified `blur(10px)` on upload/results, none on performance, with `rgba(5, 19, 14, 0.76)` surfaces. This check was made on the actual built page, not only source CSS.

Contrast was calculated against the brightest possible white photograph under the retained 60% black overlay, then composited through the 76% dark panel: muted text 8.41:1, header green 4.59:1, primary-button text 12.50:1, disabled text 6.21:1, error text 10.39:1. These conservative bounds cover every image location.

Real screenshots in `docs/screenshots/` were replaced and visually inspected for desktop, tablet and mobile. They show the final dark theme and real prediction. The background's SHA256 remains `369dbce74276e08360f97298259ebb9fb9ad3f30b410a022b5b6aee105fac577`. The final diff contains no backend, model or dataset changes. No new GPU execution checks were needed for this presentation-only change.

Antislop Delivery Gate: PASS for the frontend revision, with rule-by-rule evidence in `ANTISLOP_GATE.md`. Docker rebuild remains unverified for the reason above.

## Original delivery record

### Container deployment follow-up, 27 October 2026

After Docker Desktop became available, the owner observed the old cream interface because port 8081 was serving the previous frontend container image. The temporary Vite preview used for the redesign verification was no longer running. This was a deployment mismatch, not a missing source change.

A normal frontend Docker rebuild encountered a Docker Hub TLS timeout while fetching base-image metadata. To deploy without downloads, the already-verified `frontend/dist` assets were copied into a new image based on the locally cached frontend/Nginx image, tagged `fyp-demo-app-frontend:local` and labelled with UI revision `aaa19d623fe7a6aeba8d5ced441692788c657b56`. Only the frontend container was recreated. The temporary offline build context is ignored under `test-results/`; normal source Docker configuration remains unchanged.

HTTP verification on port 8081 confirmed index.html, JavaScript and CSS match the production build byte-for-byte. The served JavaScript contains Computational performance; the CSS contains neon green and standard backdrop-filter declarations. The background hash still matches. The existing CPU backend reported ready and completed a real Bolivia_195474 prediction: 512 × 512, four patches, 151.55 ms inference and 383.09 ms processing. These are one-request observations, not fixed benchmark claims. A fresh versioned URL was opened through the app browser tool to avoid the already-open document's cache. Browser automation was unavailable for a new visual screenshot during this follow-up; the exact same assets were visually verified in the earlier screenshots.

The full source-based Docker build remains unverified for this revision because of the external registry timeout, but the updated Docker frontend deployment and prediction path are now verified.

Date: 26 October 2026 (Asia/Kuala_Lumpur).

## Verified

- Original D4 checkpoint and all 30 sample TIFFs copied without changing bytes. Numbered folders follow the saved Bolivia test-list order.
- 18 Python tests passed on Python 3.11 with PyTorch 2.7.1. These cover the original notebook reference, all 15 paired tiles, patch placement, GeoTIFF georeferencing, invalid pixels, wrong/missing/duplicate bands and files, input size limits, samples, and unavailable-model/startup states.
- Optional CUDA test passed on the host RTX 3060, comparing full-image CPU and GPU classification.
- The optional Docker Compose GPU configuration also passed inference on all 15 pairs using the RTX 3060. The reported device was CUDA and TF32 was disabled, matching the original precision settings.
- Seven frontend tests passed, covering folder pairing and validation messages.
- Vite production build passed; self-hosted fonts are bundled. No npm audit vulnerabilities were reported during dependency installation.
- CPU Docker images built and the backend became healthy after including Rasterio's required Linux `libexpat1` library.
- All 15 samples passed through the actual Nginx/frontend and CPU backend containers: preview, prediction, thumbnail, ZIP download, and georeferenced TIFF validation.
- Linux CPU Docker reproduced the independent original-notebook reference without networking. Full preprocessed input hash matched exactly; maximum centre-crop logit difference was approximately 0.0000172, within the specified floating-point tolerance.
- A clean checkout containing only committed files built and started with Docker Compose. Its frontend, CPU model readiness, bundled documentation asset, and an actual full-image prediction passed on temporary port 8082. Only the test containers/network were then removed; the main demo remains running on port 8081.
- API mask values are 0/1/255 and preserve the source grid. Display stretches do not modify input tensors.
- The real prediction images in `docs/example-*.png` came from the CPU Docker endpoint. The example overlay was visually inspected; the no-data region is displayed as grey and the water overlay is geographically aligned.

## Updated interface verification

The simplified interface was tested in the in-app browser against the running CPU Docker app. The sample gallery, sample navigation and frontend sample requests are removed. The original performance values and centre-crop explanation remain visible.

| Control / state | Observed result |
| --- | --- |
| Initial workspace | Empty image state and disabled segmentation button |
| Choose a folder | Opened the directory chooser |
| Select a valid folder | Identified matching Bolivia_195474 files and displayed the optical preview with `Ready to segment.` |
| Segment image | Completed a real 512 × 512 D4 prediction and selected Overlay; `aria-busy=true` observed during processing |
| Segment again | Ran another prediction successfully |
| Optical / Radar / Mask / Overlay | Each control selected its corresponding image, including keyboard Space activation |
| Overlay opacity | Keyboard Home/End produced 0%/100%; PageUp restored 50%; actual overlay style matched 0.5 opacity |
| Mask PNG | Download completed; Pillow verified a 512 × 512 grayscale image |
| Overlay PNG | Download completed with the selected opacity in its filename; Pillow verified a 512 × 512 RGBA image |
| Mask GeoTIFF | Download completed; Rasterio verified 512 × 512, EPSG:4326 and nodata=255 |
| Clear | Returned to the empty state and removed preview images and download controls |
| Re-upload | Accepted a valid pair after clearing and completed prediction again |
| Missing partner | Displayed a neutral one-pair validation message; no sample-specific instructions |
| Corrupt TIFF pair | Displayed the actual decoder error and prevented segmentation |
| Service unavailable / Retry connection | A temporary stop of this app's backend produced an offline/error state with disabled inference; restart and Retry connection restored the metrics |
| Keyboard navigation | Tab exposed the skip link with visible focus; Enter focused the workspace; next Tab reached folder selection; Enter opened the chooser; Tab reached Segment; Space ran inference; Shift+Tab navigated back from opacity to Overlay |

All three actual download files were inspected. The download check identified and fixed the earlier detached data-URL anchor behaviour: PNG exports now use Blob URLs with a temporarily attached anchor. The initially observed 320px overflow was also fixed. The service-error helper now handles proxy 502/503/504 responses with actionable feedback.

## Responsive and visual checks

- Verified no horizontal overflow at 320px, 390px, 768px and 1280px viewports. At the narrowest viewport the measured page/client widths were both 305px, accounting for the scrollbar.
- Actual enabled button heights were 44px or 46px. Range control height is 44px. Keyboard focus uses a visible solid outline.
- Captured and visually inspected real desktop, tablet and mobile screenshots under `docs/screenshots/`. The hidden skip link remains clipped when unfocused.
- Text contrast: white/red 4.78:1; muted text/cream 5.93:1; muted text/secondary surface 4.86:1; white text over the brightest possible background beneath the 60% black overlay 5.74:1; error text/cream 8.10:1.
- Browser diagnostics after the final successful workflow reported no warnings or errors. Expected offline and invalid-input states were exercised separately.
- Seven frontend tests and the Vite production build passed after the final logic changes; the updated frontend container was rebuilt and exercised.
- D4 checkpoint/normalization checksums still match; all 30 original sample TIFFs remain in the repository. No model or backend inference changes were made for this UI revision.

## Antislop Delivery Gate: PASS

All four blocks passed. Rule-by-rule evidence is recorded in `ANTISLOP_GATE.md`; design purposes and the background-generation prompt are recorded in `DESIGN_NOTES.md`.

## Local environment

The owner's Oracle listener already occupies port 8080. The running demo therefore uses `FYP_APP_PORT=8081`, bound only to `127.0.0.1`. The repository default remains 8080, with the override documented in README. The Oracle listener was not changed. This app's backend was briefly stopped and restarted for the recovery test.

Model weights, sample imagery, the generated background, fonts and API documentation assets are bundled for offline runtime.
