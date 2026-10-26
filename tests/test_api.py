import base64
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np
import pytest
from fastapi.testclient import TestClient
from rasterio.io import MemoryFile
from rasterio.transform import Affine

from backend.main import app
from backend.preprocessing import InputError, MAX_FILE_BYTES, read_pair


def upload(sample_files):
    item, a, b = sample_files
    return {"s1": (item["s1"], a, "image/tiff"), "s2": (item["s2"], b, "image/tiff")}


def rewritten(blob, *, count=None, shape=None, crs=None, transform=None, descriptions=None, zero=False):
    with MemoryFile(blob) as original:
        with original.open() as src:
            profile = src.profile.copy()
            data = src.read()
            bands = src.descriptions
    if count:
        profile["count"] = count
        data = data[:count]
        bands = bands[:count]
    if shape:
        profile.update(height=shape[0], width=shape[1])
        data = data[:, :shape[0], :shape[1]]
    if crs:
        profile["crs"] = crs
    if transform:
        profile["transform"] = transform
    if zero:
        data[:] = 0
    with MemoryFile() as target:
        with target.open(**profile) as dst:
            dst.write(data)
            for index, name in enumerate(descriptions or bands, 1):
                if name:
                    dst.set_band_description(index, name)
        return target.read()


def test_health_model_docs_and_preview(client, sample_files):
    assert client.get("/api/health").json()["model_ready"]
    assert client.get("/api/model-info").json()["device"] == "cpu"
    assert client.get("/docs").status_code == 200
    assert "cdn.jsdelivr.net" not in client.get("/docs").text
    assert client.get("/api/docs-assets/swagger-ui.css").status_code == 200
    result = client.post("/api/preview", files=upload(sample_files))
    assert result.status_code == 200, result.text
    assert result.json()["rgb"].startswith("data:image/png;base64,")


def test_prediction_and_download_formats(client, sample_files):
    response = client.post("/api/predict", files=upload(sample_files))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["patch_count"] == 4
    assert result["width"] == result["height"] == 512
    assert result["inference_ms"] > 0
    assert result["processing_ms"] >= result["inference_ms"]
    for value in result["images"].values():
        assert base64.b64decode(value.split(",", 1)[1]).startswith(b"\x89PNG")
    assert base64.b64decode(result["mask_geotiff_base64"])[:2] in (b"II", b"MM")


def test_sample_pair_download_is_exact(client, sample_files):
    item, a, b = sample_files
    manifest = client.get("/api/samples").json()
    assert len(manifest) == 15
    assert client.get("/api/samples/1/thumbnail").headers["content-type"] == "image/png"
    response = client.get("/api/samples/1/download")
    with ZipFile(BytesIO(response.content)) as archive:
        assert archive.read(f"{item['folder']}/{item['s1']}") == a
        assert archive.read(f"{item['folder']}/{item['s2']}") == b
    assert client.get("/api/samples/999/download").status_code == 404


def test_missing_partner_mismatch_corrupt_and_oversized(client, sample_files):
    item, a, b = sample_files
    assert client.post("/api/preview", files={"s1": (item["s1"], a)}).status_code == 422
    for bad_file, expected in [(("Bolivia_other_S2Hand.tif", b), "different tiles"), ((item["s2"], b"not a raster"), "Cannot decode"), ((item["s2"], b"x" * (MAX_FILE_BYTES + 1)), "16 MiB")]:
        response = client.post("/api/preview", files={"s1": (item["s1"], a), "s2": bad_file})
        assert response.status_code == 422
        assert expected in response.json()["detail"]


def test_rejects_multiple_pairs_and_oversized_request(client, sample_files):
    item, a, b = sample_files
    response = client.post("/api/preview", files=[("s1", (item["s1"], a)), ("s2", (item["s2"], b)), ("s1", (item["s1"], a))])
    assert response.status_code == 422
    assert "exactly one" in response.json()["detail"]
    assert client.post("/api/preview", content=b"x", headers={"Content-Length": str(40 * 1024 * 1024)}).status_code == 413


@pytest.mark.parametrize("change,message", [
    ({"count": 12}, "requires 13 bands"),
    ({"shape": (256, 256)}, "512 × 512"),
    ({"crs": "EPSG:3857"}, "pixel alignment"),
    ({"transform": Affine(1, 0, 0, 0, -1, 100)}, "pixel alignment"),
    ({"descriptions": [f"wrong{i}" for i in range(13)]}, "band descriptions"),
])
def test_rejects_wrong_raster_structure(service, sample_files, change, message):
    item, a, b = sample_files
    with pytest.raises(InputError, match=message):
        read_pair(a, rewritten(b, **change), item["s1"], item["s2"], service.statistics)


def test_invalid_pixels_stay_finite_and_are_not_background(service, sample_files):
    item, a, b = sample_files
    with MemoryFile(b) as original:
        with original.open() as src:
            profile, values, descriptions = src.profile.copy(), src.read(), src.descriptions
    values[:, :20, :20] = 0
    with MemoryFile() as modified:
        with modified.open(**profile) as dst:
            dst.write(values)
            for index, name in enumerate(descriptions, 1):
                dst.set_band_description(index, name)
        pair = read_pair(a, modified.read(), item["s1"], item["s2"], service.statistics)
    assert np.isfinite(pair.tensor).all()
    assert np.all(pair.tensor[2:, :20, :20] == 0)
    mask, _ = service.predict(pair)
    assert np.all(mask[:20, :20] == 255)


def test_unavailable_model_is_reported(client):
    service = app.state.predictor
    try:
        app.state.predictor = None
        assert client.get("/api/health").status_code == 503
        assert client.get("/api/model-info").status_code == 503
    finally:
        app.state.predictor = service


def test_failed_startup_keeps_health_endpoint_available():
    with patch("backend.main.Predictor", side_effect=RuntimeError("missing weights")):
        with TestClient(app) as client:
            assert client.get("/api/health").status_code == 503
            assert "Model unavailable" in client.get("/api/model-info").json()["detail"]
