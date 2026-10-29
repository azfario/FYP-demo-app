# JRC water separation verification

Verified on 29 October 2026 on branch `permanent-water-vs-flood-pixel`, based on
`hand-test-data` commit `78de32e`.

## Automated and browser checks

- **52 backend tests passed**, including all pre-existing prediction/evaluation
  tests, known synthetic water classes, ignored pixels, empty/full references,
  missing/invalid manifests, missing/corrupt TIFFs, checksum failures, geographic
  mismatch, nonbinary values and all-nodata references. The existing FastAPI
  test-client dependency emits a deprecation warning; no test failed.
- **12 frontend tests passed** and the Vite production build passed.
- All **446 reference checksums and binary encodings** verified. The preparation
  script also checked every reference against its original satellite grid.
- All **10 paired demos** passed real HTTP prediction through the local app.
  Classified and candidate-flood GeoTIFF arrays were independently recomputed
  from the original predicted water and supplied JRC map; geography, nodata,
  counts and reference checksum metadata matched. Report:
  `test-results/water-demo-report.json` (generated, not committed).
- Both workspaces passed real browser uploads, Water types default selection,
  all imagery/reference views, keyboard controls, opacity 0/50/100, six actual
  downloads per workspace, unchanged water comparisons, Clear/re-upload, tab
  state retention, upload errors and service Retry. No uncaught page errors.
- The unavailable-JRC UI case used recorded real prediction/preview responses
  with separation marked unavailable. It retained water results and disabled
  separation controls. Backend tests separately exercised real reference failures.
- No horizontal overflow at 320, 390, 768 or 1280px. Enabled buttons retained at
  least 44px height. New desktop/mobile screenshots were visually inspected.
- Downloaded PNG overlays at 50% opacity matched an independent Pillow blend
  within one intensity level of browser rounding. Downloaded TIFF pixels and
  metadata matched independently recomputed classes in both workspaces.

## Demonstration observations

These are pixel counts from a single local CUDA demonstration run, not accuracy
measurements. Seven examples produced both detected water classes; three have
valid all-zero historical JRC references.

| Demo | Tile | Detected permanent water | Candidate floodwater | Excluded |
| --- | --- | ---: | ---: | ---: |
| 01 | India_900498 | 53,254 | 68,283 | 0 |
| 02 | India_399883 | 32,422 | 97,720 | 0 |
| 03 | India_747992 | 0 | 115,301 | 0 |
| 04 | India_591317 | 76,671 | 34,270 | 0 |
| 05 | Nigeria_812045 | 16,503 | 111,265 | 579 |
| 06 | Spain_7387658 | 17,773 | 131,869 | 0 |
| 07 | Spain_7370579 | 0 | 75,681 | 0 |
| 08 | Paraguay_1029191 | 37,840 | 13,054 | 0 |
| 09 | Paraguay_790830 | 25,729 | 6,093 | 0 |
| 10 | Somalia_322855 | 0 | 45,932 | 0 |

## Reproduction

```powershell
python -m pytest -q
cd frontend
npm test
npm run build
cd ..
python scripts/check_water_demo.py --base-url http://127.0.0.1:5173
```

The browser check is `node scripts/check_ui.cjs`, with `UI_BASE_URL` pointing to
the running app. Set `NODE_PATH` if Playwright is supplied externally and
`PLAYWRIGHT_CHROMIUM_EXECUTABLE` to an installed browser if needed. This run used
local Uvicorn/Vite and installed Chrome initially. The subsequent Docker
verification below exercised the same feature through Nginx and Linux CPU PyTorch.

## Docker verification, 29-30 October 2026

- Both original Dockerfiles built successfully. Frontend: Node production build
  plus Nginx; backend: Python 3.11 plus PyTorch CPU. No Dockerfile or application
  changes were needed for this verification.
- The first cold backend build timed out downloading Rasterio from
  `files.pythonhosted.org`, after very slow dependency downloads. A subsequent
  standard build succeeded using the previous successful official Python base
  and cached dependency layers. This establishes cached-build and runtime
  success; it does not establish an uninterrupted fresh-download build.
- The locally cached official Python base was
  `sha256:90d117a7f1ef6535dc75831e1a9184725757fede0d4d424d7977fb5429d50610`.
  Its content was retrieved by digest from Google's Docker Hub mirror and tagged
  locally as `python:3.11-slim-bookworm`. The repository's Dockerfile was unchanged.
- Successful backend image:
  `sha256:75ae4866e326cab6750d48436d73ca0945e152b86927e391bea19b0d03f08f20`.
  Frontend image:
  `sha256:76cdcb543a86988b2c73a9253ac90a5dfb96c7ffa2ddd0f1d3ca6734ea1ace46`.
- Started isolated Compose project `fyp-water-verify`, bound only to
  `127.0.0.1:8082`, with no source bind mounts. Backend health passed; Nginx served
  the frontend and forwarded real uploads/predictions.
- All **446 bundled JRC reference checksums** matched inside the non-root
  container (UID 10001). The water-separation source checksum matched the feature
  commit exactly: `6febe6c21967923ab711564288921e820e0cb17e2c17fd192443bdba9290ef5b`.
- All **10 paired demonstrations** passed through Nginx. Independent checks
  confirmed classified/candidate-flood pixel values, reference provenance,
  geography, nodata and counts. Their CPU class counts matched the table above.
- All **10 Hand Test triplets** passed preview and prediction; uploaded-reference
  IoU, Dice and pixel accuracy matched independent calculations. Served HTML/JS/CSS
  matched the local production build byte-for-byte; original model and background
  were retained.
- Both workspaces passed the browser script against Docker: all six image views
  (plus Hand Test Compare), opacity, six downloads per workspace, keyboard
  controls, 320/390/768/1280px layouts, reset/error handling and service recovery.
  There were no uncaught page errors. Screenshots now show the actual CPU Docker
  deployment. Generated reports remain under ignored `test-results/`.
- Only the isolated test containers/network were removed after verification;
  built images and dependency caches were retained. Existing app services were
  not stopped or recreated. The optional GPU image was outside this verification.

Reproduce using the normal CPU configuration:

```powershell
docker compose build
docker compose up -d --no-build --wait
python scripts/check_water_demo.py --base-url http://127.0.0.1:8081
```

The example URL uses this workspace's `.env` port override (8081); the repository
default is 8080. Use the port selected for your deployment. Downloading uncached
base images and Python dependencies requires working external registry/PyPI access.

## Interpretation

No weights, model preprocessing or training code changed. Existing water scores
are preserved. The neural network still predicts water; JRC supplies historical
context after inference. Candidate floodwater is not independently validated
flood truth, and seasonal water and model/reference errors may remain. The
supplied references' exact derivation dates/threshold are not established here.
