# Ten paired water-separation demonstrations

In **Segmentation**, choose one numbered `demo` folder and click **Segment image**.
Start with **demo 01**. Each folder contains exactly two original Sen1Floods11 TIFFs:
Sentinel-1 and Sentinel-2. JRC references are matched automatically by the backend;
do not add a JRC TIFF or label to these upload folders.

| Folder | Tile | Corresponding Hand Test folder | JRC permanent water |
| --- | --- | --- | --- |
| demo 01 | India_900498 | hand test 1 | Present |
| demo 02 | India_399883 | hand test 2 | Present |
| demo 03 | India_747992 | hand test 3 | None marked |
| demo 04 | India_591317 | hand test 4 | Present |
| demo 05 | Nigeria_812045 | hand test 5 | Present |
| demo 06 | Spain_7387658 | hand test 6 | Present |
| demo 07 | Spain_7370579 | hand test 7 | None marked |
| demo 08 | Paraguay_1029191 | hand test 8 | Present |
| demo 09 | Paraguay_790830 | hand test 9 | Present |
| demo 10 | Somalia_322855 | hand test 10 | None marked |

For **Hand Test**, select the corresponding folder under `hand test/`, containing
the additional original hand-labelled water reference. Those scores still measure
water segmentation, not independently verified flood-only accuracy.

Water types shows **blue detected permanent water** and **orange candidate
floodwater**. The JRC reference view shows the historical mask independently of
the prediction. Demos 03, 07 and 10 have valid all-zero JRC references, so their
predicted water is entirely candidate floodwater where imagery is valid. An empty
reference does not prove that permanent water is absent in reality.

These are selected demonstrations from the original Hand Test split, not a
representative benchmark or a selection based on prediction scores. Seasonal
water and model/reference errors can remain. No individual prediction outcome is
guaranteed. `manifest.json` records original filenames, SHA256 checksums, sizes,
source split and matching Hand Test folders. TIFF bytes and geography are preserved.

Source: [Sen1Floods11, Cloud to Street](https://github.com/cloudtostreet/Sen1Floods11).
JRC reference attribution: EC JRC/Google. See the repository README for citation
and third-party data terms. This repository grants no new data license.

Reproduce the copies and bundled references from the original v1.1 tree:

```powershell
python scripts/prepare_water_demo.py --source 'C:\path\to\sen1floods11\v1.1'
```
