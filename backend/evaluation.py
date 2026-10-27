"""Evaluate predictions against a reference without changing model inputs."""
from dataclasses import dataclass

import numpy as np
from rasterio.errors import RasterioError
from rasterio.io import MemoryFile

from .preprocessing import InputError, MAX_FILE_BYTES, tile_name
from .visualization import png_url


@dataclass
class Reference:
    labels: np.ndarray
    valid: np.ndarray


def read_reference(blob, filename, pair):
    if tile_name(filename, "Label") != pair.tile_id:
        raise InputError("Ground truth and satellite filenames identify different tiles.")
    if not blob:
        raise InputError("The ground-truth TIFF must contain data.")
    if len(blob) > MAX_FILE_BYTES:
        raise InputError("Each TIFF must be 16 MiB or smaller.")
    try:
        with MemoryFile(blob) as memory, memory.open() as src:
            if src.driver != "GTiff" or src.count != 1:
                raise InputError("Ground truth must be a single-band GeoTIFF.")
            if (src.height, src.width) != (512, 512):
                raise InputError("Ground truth must be 512 × 512 pixels.")
            if src.crs != pair.profile["crs"] or not src.transform.almost_equals(pair.profile["transform"], precision=1e-9):
                raise InputError("Ground truth must share the satellite coordinate system and pixel alignment.")
            # Raw labels intentionally preserve background=0 even when nodata metadata is 0.
            labels = src.read(1)
    except InputError:
        raise
    except (RasterioError, ValueError, TypeError, OverflowError) as exc:
        raise InputError("Cannot decode ground truth. Use the original LabelHand GeoTIFF.") from exc
    if not np.isfinite(labels).all() or not np.isin(labels, [-1, 0, 1, 255]).all():
        raise InputError("Ground truth requires 0=background, 1=water, and -1 or 255=ignored.")
    valid = pair.valid & np.isin(labels, [0, 1])
    if not valid.any():
        raise InputError("The triplet contains no pixels valid in both satellite imagery and ground truth.")
    return Reference(labels.astype(np.int16), valid)


def evaluate_mask(prediction, reference):
    valid = reference.valid
    predicted = prediction[valid] == 1
    actual = reference.labels[valid] == 1
    tp = int(np.count_nonzero(predicted & actual))
    fp = int(np.count_nonzero(predicted & ~actual))
    fn = int(np.count_nonzero(~predicted & actual))
    tn = int(np.count_nonzero(~predicted & ~actual))
    count = tp + fp + fn + tn

    def ratio(numerator, denominator):
        return numerator / denominator if denominator else None

    return {"iou": ratio(tp, tp + fp + fn), "dice": ratio(2 * tp, 2 * tp + fp + fn),
            "pixel_accuracy": ratio(tp + tn, count), "evaluated_pixels": count,
            "excluded_pixels": int(valid.size - count), "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}}


def comparison_images(reference, prediction=None):
    def render(values):
        image = np.where(values == 1, 255, 0).astype(np.uint8)
        image[~reference.valid] = 120
        return png_url(image)

    images = {"ground_truth": render(reference.labels)}
    if prediction is not None:
        images["comparison_prediction"] = render(prediction)
    return images
