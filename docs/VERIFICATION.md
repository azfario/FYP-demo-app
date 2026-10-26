# Verification record

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
