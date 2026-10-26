import base64
import hashlib
from pathlib import Path

import numpy as np
import pytest
from rasterio.io import MemoryFile
import torch

from backend.inference import Predictor
from backend.preprocessing import read_pair
from backend.visualization import geotiff_base64, previews
from conftest import ROOT


def test_original_notebook_preprocessing_and_center_prediction(service, pair):
    reference = np.load(Path(__file__).parent / "fixtures/d4_reference.npz")
    assert hashlib.sha256(pair.tensor.tobytes()).hexdigest() == str(reference["input_sha256"])
    with torch.inference_mode():
        logits = service.model(torch.from_numpy(np.ascontiguousarray(pair.tensor[None, :, 128:384, 128:384]))).numpy()
    np.testing.assert_allclose(logits, reference["center_logits"], rtol=1e-4, atol=1e-4)


def test_all_fifteen_pairs_produce_full_spatially_aligned_masks(service, records):
    assert len(records) == 15
    assert len(list((ROOT / "sample").rglob("*.tif"))) == 30
    for item in records:
        folder = ROOT / "sample" / item["folder"]
        pair = read_pair((folder / item["s1"]).read_bytes(), (folder / item["s2"]).read_bytes(), item["s1"], item["s2"], service.statistics)
        mask, elapsed = service.predict(pair)
        assert mask.shape == (512, 512)
        assert set(np.unique(mask)).issubset({0, 1, 255})
        assert elapsed > 0
        assert np.all(mask[~pair.valid] == 255)
        with MemoryFile(base64.b64decode(geotiff_base64(pair, mask))) as mem:
            with mem.open() as src:
                assert src.crs == pair.profile["crs"]
                assert src.transform == pair.profile["transform"]
                assert src.nodata == 255
                np.testing.assert_array_equal(src.read(1), mask)


def test_patch_placement_matches_each_independent_forward(service, pair):
    mask, _ = service.predict(pair)
    with torch.inference_mode():
        for row in (0, 256):
            for col in (0, 256):
                x = torch.from_numpy(np.ascontiguousarray(pair.tensor[None, :, row:row + 256, col:col + 256]))
                expected = (service.model(x).sigmoid().numpy()[0, 0] > 0.5).astype(np.uint8)
                expected[~pair.valid[row:row + 256, col:col + 256]] = 255
                np.testing.assert_array_equal(mask[row:row + 256, col:col + 256], expected)


def test_display_adjustments_do_not_change_model_input(pair):
    original = pair.tensor.copy()
    rgb, radar = previews(pair)
    assert rgb.shape == (512, 512, 3)
    assert radar.shape == (512, 512)
    np.testing.assert_array_equal(pair.tensor, original)


@pytest.mark.gpu
def test_cuda_matches_cpu_classification(service, pair):
    if not torch.cuda.is_available():
        pytest.skip("No CUDA device exposed to this runtime")
    gpu = Predictor(ROOT)
    assert gpu.device.type == "cuda"
    cpu_mask, _ = service.predict(pair)
    gpu_mask, _ = gpu.predict(pair)
    assert np.mean(cpu_mask == gpu_mask) > 0.9999
