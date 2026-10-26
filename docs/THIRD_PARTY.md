# Bundled third-party material

- **Inter 5.3.0**: SIL Open Font License 1.1. The license is included in `Inter-LICENSE.txt`; font files are supplied by the pinned `@fontsource/inter` npm package and bundled into the frontend build.
- **Swagger UI 5.34.0**: Apache License 2.0. Unmodified distribution assets are vendored under `backend/static/docs/`, along with LICENSE, NOTICE, and the JavaScript bundle's license notice. The source npm dependency is pinned in the frontend lockfile.
- **Sen1Floods11 v1.1**: the original 15 Bolivia S1/S2 pairs, with names, values, coordinate systems, and metadata preserved. Dataset attribution and paper citation appear in the main README. The dataset's original terms remain applicable; no new third-party data license is granted by this repository.
- **D4 checkpoint**: the owner's trained FYP checkpoint, copied byte-for-byte. Architecture is ported verbatim from the selected notebook snapshot. Checkpoint and normalization SHA256 values are recorded in `models/model_info.json`.

Other runtime/build dependencies retain their upstream licenses and package metadata. The supplied design and stack documents are retained as owner-provided references under `docs/`.
