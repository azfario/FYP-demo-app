# Selected Hand Test demonstrations

Ten Sen1Floods11 v1.1 Hand Test triplets, selected by visual inspection of river/floodplain water patterns, without ranking D4 prediction scores. They are demonstrations, not a representative benchmark of the full 90-tile Hand Test split.

| Folder | Tile |
| --- | --- |
| hand test 1 | India_900498 |
| hand test 2 | India_399883 |
| hand test 3 | India_747992 |
| hand test 4 | India_591317 |
| hand test 5 | Nigeria_812045 |
| hand test 6 | Spain_7387658 |
| hand test 7 | Spain_7370579 |
| hand test 8 | Paraguay_1029191 |
| hand test 9 | Paraguay_790830 |
| hand test 10 | Somalia_322855 |

Each numbered folder contains the original matching `_S1Hand.tif`, `_S2Hand.tif` and `_LabelHand.tif` files. Exactly 30 TIFFs, approximately 37.4 MiB. Filenames, raster bytes and georeferencing are unchanged. All ten are in `flood_test_data.csv`, with no overlap with the training or validation lists. The manifest records original-file SHA256 hashes, the source split hash and each selection reason.

In the app, select **Hand Test**, then choose one numbered folder, not this parent directory. The reference mask appears before inference; click **Segment image** for prediction and full-image comparison scores. Changing only the reference changes the comparison, not model prediction.

Labels: `0=background`, `1=water`, `-1/255=ignored`. Scores use only pixels valid in both imagery and labels. Zero remains background even when label nodata metadata says zero. The app requires the original aligned 512 × 512 rasters; it never resizes or reprojects labels. Grey areas in Compare are excluded from scoring. Water includes permanent water; this is not a change-detection product that establishes newly flooded land.

After prediction, **Compare** stays selected, including when clicking Segment again.
Choose **Permanent water vs flood** to see the automatically matched historical
JRC map applied to the prediction. Blue marks detected permanent water, red marks candidate floodwater,
black marks background and grey marks no-data. This view is a solid class mask.
Choose **Compare** to view the original water comparison. Scores still measure
all-water segmentation. **JRC reference** shows the historical reference itself;
three selected tiles have valid all-zero references. For two-file Segmentation
uploads, use the corresponding numbered folders under `demo pairs/`.

Source: [Sen1Floods11, Cloud to Street](https://github.com/cloudtostreet/Sen1Floods11). Citation and attribution are in the [repository README](../README.md#dataset-attribution). This repository does not grant a new license for third-party data.

To reproduce the copies from an existing original v1.1 directory:

```powershell
python scripts/prepare_hand_test.py --source 'C:\path\to\sen1floods11\v1.1'
```
