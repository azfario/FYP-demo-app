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
local Uvicorn/Vite and installed Chrome because Docker Desktop was not running.
Docker packaging includes `references/`; a new Docker build/runtime was not
verified during this feature change. Previous Docker results elsewhere in the
repository refer to earlier versions.

## Interpretation

No weights, model preprocessing or training code changed. Existing water scores
are preserved. The neural network still predicts water; JRC supplies historical
context after inference. Candidate floodwater is not independently validated
flood truth, and seasonal water and model/reference errors may remain. The
supplied references' exact derivation dates/threshold are not established here.
