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
- API mask values are 0/1/255 and preserve the source grid. Display stretches do not modify input tensors.
- The real prediction images in `docs/example-*.png` came from the CPU Docker endpoint. The example overlay was visually inspected; the no-data region is displayed as grey and the water overlay is geographically aligned.

## Browser observations and click-through evidence

The desktop browser displayed the running app and actual model metadata. The following sequence was observed:

| Control / state | Observed result |
| --- | --- |
| Initial workspace | Empty image state and disabled segmentation button |
| Choose a folder | Opened the directory chooser |
| Select `sample/bolivia 1` | Identified both matching filenames and showed the validating state |
| Validation completes | Showed optical preview and `Pair checked. Ready to segment.` |
| Segment this image | Completed a real D4 prediction and selected the overlay view |
| Completed result | Showed 512 × 512 dimensions, four patches, actual execution device, measured timing, opacity control, and download controls |

Further browser automation stopped because Computer Use could not determine the current Chrome URL with sufficient confidence to enforce its policy. It was not retried or bypassed through another UI automation technology.

## Antislop Delivery Gate status: pending final browser verification

No full Delivery Gate PASS is claimed. This is a working implementation with remaining UI verification, not a fully verified UI release.

| Gate block | Evidence / remaining work |
| --- | --- |
| Hard Gate | Build, real upload and prediction observed; validation is covered by API/frontend tests. Core text contrasts were calculated: white on primary red 4.78:1; muted text on cream 5.68:1. Visible keyboard focus and 44px control sizing are implemented. Full mobile/keyboard and remaining-control click-through still need browser verification. |
| Purpose-Gate | Major visual decisions and their purposes are recorded in DESIGN_NOTES.md. No decorative gradients, icon libraries, invented identity assets, or fictional statistics are used. |
| Liveliness | ENERGY 2 / RHYTHM 2 / MOTION 1 declared. Image-first composition, asymmetric workspace, structural whitespace, one primary red action, and real satellite gallery implemented; desktop initial view inspected. Responsive views still require visual inspection. |
| Craftsmanship and Quality Locks | Empty, validating, ready, processing, success, and error states implemented. Real model/data/API behaviour tested. No dead navigation targets or second theme shipped. Remaining interaction and breakpoint verification prevents a final PASS. |

Still to verify in the browser: Optical/Radar/Mask/Overlay switching, opacity changes and overlay downloads, all download controls, clear/re-upload and error recovery, all navigation targets, keyboard-only operation, console errors, and mobile/tablet/narrow layouts. Export real UI screenshots after these checks.

## Local environment

The owner's Oracle listener already occupies port 8080. The running demo therefore uses `FYP_APP_PORT=8081`, bound only to `127.0.0.1`. The repository default remains 8080, with the override documented in README. No existing service was stopped or reconfigured.

Model and sample weights are bundled for offline runtime. API documentation assets are self-hosted as well.
