import base64
import hashlib
from io import BytesIO
import json
from unittest.mock import patch

import numpy as np
from PIL import Image
import pytest
from rasterio.io import MemoryFile
from rasterio.transform import Affine

from backend.evaluation import Reference, comparison_images, evaluate_mask, read_reference
from backend.preprocessing import InputError, MAX_FILE_BYTES, read_pair
from conftest import ROOT


@pytest.fixture
def hand_records():
    return json.loads((ROOT / "hand test/manifest.json").read_text())["samples"]


def triplet(item):
    folder = ROOT / "hand test" / item["folder"]
    return {key: (entry["filename"], (folder / entry["filename"]).read_bytes(), "image/tiff")
            for key, entry in item["files"].items()}


@pytest.fixture
def hand_files(hand_records):
    return triplet(hand_records[0])


@pytest.fixture
def hand_pair(service, hand_files):
    a, b = hand_files["s1"], hand_files["s2"]
    return read_pair(a[1], b[1], a[0], b[0], service.statistics)


def reference_blob(original, *, values=None, shape=None, count=1, crs=None, transform=None, nodata=None):
    with MemoryFile(original) as mem, mem.open() as src:
        profile = src.profile.copy()
        labels = src.read(1) if values is None else values
    if shape:
        labels = labels[:shape[0], :shape[1]]
    profile.update(count=count, height=labels.shape[0], width=labels.shape[1], dtype=labels.dtype, nodata=nodata)
    if crs:
        profile["crs"] = crs
    if transform:
        profile["transform"] = transform
    with MemoryFile() as target:
        with target.open(**profile) as dst:
            dst.write(np.stack([labels] * count))
        return target.read()


def test_known_confusion_counts_and_ignored_pixels():
    reference = Reference(np.array([1, 1, 0, 0, -1]), np.array([True, True, True, True, False]))
    result = evaluate_mask(np.array([1, 0, 1, 0, 1]), reference)
    assert result == {"iou": 1 / 3, "dice": .5, "pixel_accuracy": .5,
                      "evaluated_pixels": 4, "excluded_pixels": 1,
                      "confusion": {"tp": 1, "fp": 1, "fn": 1, "tn": 1}}


@pytest.mark.parametrize("prediction,truth,valid,expected", [
    ([1, 0], [1, 0], [True, True], (1, 1, 1)),
    ([0, 1], [1, 0], [True, True], (0, 0, 0)),
    ([0, 0], [0, 0], [True, True], (None, None, 1)),
    ([1, 0], [0, 0], [True, True], (0, 0, .5)),
    ([1, 0], [1, 0], [False, False], (None, None, None)),
])
def test_metric_edge_cases(prediction, truth, valid, expected):
    result = evaluate_mask(np.array(prediction), Reference(np.array(truth), np.array(valid)))
    assert tuple(result[key] for key in ("iou", "dice", "pixel_accuracy")) == expected


def test_ignored_values_sensor_invalidity_and_nodata_zero(hand_files, hand_pair):
    values = np.zeros((512, 512), dtype=np.int16)
    values[0, :4] = [0, 1, -1, 255]
    hand_pair.valid[1, 0] = False
    ref = read_reference(reference_blob(hand_files["ground_truth"][1], values=values, nodata=0), hand_files["ground_truth"][0], hand_pair)
    assert ref.valid[0, 0] and ref.valid[0, 1]
    assert not ref.valid[0, 2:4].any() and not ref.valid[1, 0]
    images = comparison_images(ref, np.ones((512, 512), dtype=np.uint8))
    for url in images.values():
        pixels = np.array(Image.open(BytesIO(base64.b64decode(url.split(",", 1)[1]))))
        assert np.all(pixels[~ref.valid] == 120)


@pytest.mark.parametrize("change,message", [
    ({"count": 2}, "single-band"),
    ({"shape": (256, 256)}, "512"),
    ({"crs": "EPSG:3857"}, "pixel alignment"),
    ({"transform": Affine(1, 0, 1, 0, -1, 100)}, "pixel alignment"),
    ({"values": np.full((512, 512), 2, dtype=np.int16)}, "0=background"),
    ({"values": np.full((512, 512), np.nan, dtype=np.float32)}, "0=background"),
    ({"values": np.full((512, 512), -1, dtype=np.int16)}, "no pixels valid"),
])
def test_reference_rejects_invalid_rasters(hand_files, hand_pair, change, message):
    with pytest.raises(InputError, match=message):
        read_reference(reference_blob(hand_files["ground_truth"][1], **change), hand_files["ground_truth"][0], hand_pair)


def test_reference_rejects_bad_identity_corruption_and_size(hand_files, hand_pair):
    name, blob, _ = hand_files["ground_truth"]
    for data, filename, message in [(blob, "Other_123_LabelHand.tif", "different tiles"),
                                    (b"bad", name, "Cannot decode"), (b"", name, "contain data"),
                                    (b"x" * (MAX_FILE_BYTES + 1), name, "16 MiB"),
                                    (blob, "../" + name, "not paths")]:
        with pytest.raises(InputError, match=message):
            read_reference(data, filename, hand_pair)


def test_triplet_api_validation_and_limits(client, hand_files):
    assert client.post("/api/hand-test/preview", files={k: v for k, v in hand_files.items() if k != "ground_truth"}).status_code == 422
    assert client.post("/api/hand-test/preview", files=[*hand_files.items(), ("ground_truth", hand_files["ground_truth"])]).status_code == 422
    assert client.post("/api/hand-test/preview", files={**hand_files, "extra": ("x.txt", b"x")}).status_code == 422
    for field in ("s1", "s2", "ground_truth"):
        response = client.post("/api/hand-test/preview", files={**hand_files, field: (hand_files[field][0], b"bad", "image/tiff")})
        assert response.status_code == 422
    assert client.post("/api/hand-test/preview", content=b"x", headers={"Content-Length": str(49 * 1024 * 1024)}).status_code == 413
    # The triplet request ceiling is larger, while original pair endpoints retain 32 MiB.
    assert client.post("/api/hand-test/preview", content=b"x", headers={"Content-Length": str(34 * 1024 * 1024)}).status_code == 422
    assert client.post("/api/preview", content=b"x", headers={"Content-Length": str(34 * 1024 * 1024)}).status_code == 413


def test_all_ten_triplets_and_independent_full_image_scores(client, hand_records):
    assert len(hand_records) == 10
    assert len(list((ROOT / "hand test").rglob("*.tif"))) == 30
    for item in hand_records:
        files = triplet(item)
        assert not item["in_training_split"] and not item["in_validation_split"]
        for key, (_, blob, _) in files.items():
            assert hashlib.sha256(blob).hexdigest() == item["files"][key]["sha256"]
        preview = client.post("/api/hand-test/preview", files=files)
        assert preview.status_code == 200, preview.text
        assert "ground_truth" in preview.json()
        response = client.post("/api/hand-test/predict", files=files)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["width"] == result["height"] == 512 and result["patch_count"] == 4
        assert result["processing_ms"] >= result["inference_ms"] > 0
        with MemoryFile(base64.b64decode(result["mask_geotiff_base64"])) as mem, mem.open() as src:
            prediction = src.read(1)
            assert src.nodata == 255
            transform, crs = src.transform, src.crs
        with MemoryFile(files["ground_truth"][1]) as mem, mem.open() as src:
            truth = src.read(1)
            assert src.transform.almost_equals(transform, precision=1e-9) and src.crs == crs
        valid = np.isin(truth, [0, 1]) & (prediction != 255)
        actual_water = truth[valid] == 1
        predicted_water = prediction[valid] == 1
        overlap = np.logical_and(actual_water, predicted_water).sum()
        union = np.logical_or(actual_water, predicted_water).sum()
        e = result["evaluation"]
        assert e["evaluated_pixels"] == int(valid.sum())
        assert e["excluded_pixels"] == int((~valid).sum())
        assert e["iou"] == pytest.approx(overlap / union)
        assert e["dice"] == pytest.approx(2 * overlap / (actual_water.sum() + predicted_water.sum()))
        assert e["pixel_accuracy"] == pytest.approx(np.mean(actual_water == predicted_water))
        for key in ("ground_truth", "comparison_prediction"):
            image = np.array(Image.open(BytesIO(base64.b64decode(result["images"][key].split(",", 1)[1]))))
            assert image.shape == (512, 512)
            assert np.all(image[~valid] == 120)


def test_ground_truth_never_changes_prediction(client, hand_files):
    first = client.post("/api/hand-test/predict", files=hand_files).json()
    filename, blob, _ = hand_files["ground_truth"]
    with MemoryFile(blob) as mem, mem.open() as src:
        values = src.read(1)
    valid = np.isin(values, [0, 1])
    values[valid] = 1 - values[valid]
    altered = {**hand_files, "ground_truth": (filename, reference_blob(blob, values=values), "image/tiff")}
    second = client.post("/api/hand-test/predict", files=altered).json()
    original = client.post("/api/predict", files={k: v for k, v in hand_files.items() if k != "ground_truth"}).json()
    assert first["mask_geotiff_base64"] == second["mask_geotiff_base64"] == original["mask_geotiff_base64"]
    assert first["evaluation"] != second["evaluation"]


def test_empty_water_metrics_serialize_as_null(client, service, hand_files):
    filename, blob, _ = hand_files["ground_truth"]
    background = reference_blob(blob, values=np.zeros((512, 512), dtype=np.int16))
    files = {**hand_files, "ground_truth": (filename, background, "image/tiff")}
    with patch.object(service, "predict", return_value=(np.zeros((512, 512), dtype=np.uint8), 1.0)):
        result = client.post("/api/hand-test/predict", files=files)
    assert result.status_code == 200
    assert result.json()["evaluation"]["iou"] is None
    assert result.json()["evaluation"]["dice"] is None
    assert result.json()["evaluation"]["pixel_accuracy"] == 1


def test_hand_test_unavailable_model_returns_service_error(client, hand_files):
    from backend.main import app
    with patch.object(app.state, "predictor", None):
        response = client.post("/api/hand-test/preview", files=hand_files)
        assert response.status_code == 503
        assert "starting" in response.json()["detail"]
