# Historical JRC permanent-water references

`jrc/` contains all 446 original Sen1Floods11 v1.1 `JRCWaterHand` TIFFs,
unchanged. `jrc/manifest.json` records provenance, byte sizes and SHA256 checksums.
The supplied rasters contain binary values: 0 outside the permanent-water
reference, 1 permanent water. All have one band, no declared nodata value and
match the original satellite grid. Their band description is `occurrence`, but
their actual values are already binary: no percentage threshold is applied.

These are the dataset's historical reference masks, not a verified observation
immediately before each event. Exact source dates and the derivation threshold
have not been independently established. The app does not claim real-time
flood detection or independent validation of these references.

At runtime the backend checks the checksum, geography, encoding and valid pixels.
Water predictions remain available if a reference cannot be used. Original model
predictions and hand-labelled water metrics are unaffected by JRC separation.

Source: [Sen1Floods11 documentation](https://github.com/cloudtostreet/Sen1Floods11/blob/master/docs/README.md).
Attribution: EC JRC/Google via Cloud to Street. Third-party data retains its
original terms; no new license is granted by this repository.
