"""Validate paired Sen1Floods11 rasters and reproduce D4 preprocessing."""
from dataclasses import dataclass
import re

import numpy as np
from rasterio.io import MemoryFile
from rasterio.errors import RasterioError

MAX_FILE_BYTES = 16 * 1024 * 1024
S1_BANDS = ("VV", "VH")
S2_BANDS = ("B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B9", "B10", "B11", "B12")


class InputError(ValueError):
    pass


@dataclass
class Pair:
    tile_id: str
    tensor: np.ndarray
    s1_raw: np.ndarray
    s2_raw: np.ndarray
    valid: np.ndarray
    profile: dict


def tile_name(name: str, sensor: str) -> str:
    if "/" in name or "\\" in name:
        raise InputError("Send TIFF filenames, not paths.")
    match = re.fullmatch(r"(.+)_" + sensor + r"Hand\.tiff?", name, re.IGNORECASE)
    if not match:
        raise InputError(f"Expected a dataset filename such as Bolivia_103757_{sensor}Hand.tif.")
    return match.group(1)


def read_pair(s1_bytes, s2_bytes, s1_name, s2_name, statistics):
    identity = tile_name(s1_name, "S1")
    if identity != tile_name(s2_name, "S2"):
        raise InputError("The S1 and S2 filenames identify different tiles. Choose a matching pair.")
    for blob in (s1_bytes, s2_bytes):
        if not blob:
            raise InputError("Both TIFF files must contain data.")
        if len(blob) > MAX_FILE_BYTES:
            raise InputError("Each TIFF must be 16 MiB or smaller.")
    try:
        with MemoryFile(s1_bytes) as m1, MemoryFile(s2_bytes) as m2:
            with m1.open() as a, m2.open() as b:
                for src, bands, sensor in ((a, S1_BANDS, "S1"), (b, S2_BANDS, "S2")):
                    if src.driver != "GTiff":
                        raise InputError(f"{sensor} must be a GeoTIFF.")
                    if src.count != len(bands):
                        raise InputError(f"{sensor} requires {len(bands)} bands; received {src.count}.")
                    if (src.height, src.width) != (512, 512):
                        raise InputError("This demo accepts 512 × 512 pixel Sen1Floods11 tiles.")
                    if tuple(src.descriptions) != bands:
                        raise InputError(f"{sensor} band descriptions must be in this order: {', '.join(bands)}.")
                    if src.crs is None:
                        raise InputError(f"{sensor} has no coordinate reference system.")
                if a.crs != b.crs or not a.transform.almost_equals(b.transform, precision=1e-9):
                    raise InputError("S1 and S2 must have the same coordinate system and pixel alignment.")
                s1_raw = a.read().astype(np.float32)
                s2_masked = b.read(masked=True).astype(np.float32)
                s2_raw = np.asarray(s2_masked.data)
                s2_valid = ~np.ma.getmaskarray(s2_masked) & np.isfinite(s2_raw)
                valid = (a.read_masks() > 0).all(axis=0) & np.isfinite(s1_raw).all(axis=0) & s2_valid.any(axis=0)
                profile = a.profile.copy()
    except InputError:
        raise
    except (RasterioError, ValueError, TypeError, OverflowError) as exc:
        raise InputError("Cannot decode the TIFF pair. Use the original dataset GeoTIFF files.") from exc
    if not valid.any():
        raise InputError("The pair contains no usable satellite pixels.")
    # S1's replacement-before-clipping order matches the original dataset class.
    s1 = np.nan_to_num(s1_raw, nan=0.0, posinf=0.0, neginf=0.0)
    s1 = (np.clip(s1, -50.0, 1.0) + 50.0) / 51.0
    mean = np.asarray(statistics["mean"], dtype=np.float32)[:, None, None]
    std = np.asarray(statistics["std"], dtype=np.float32)[:, None, None]
    safe = np.where(s2_valid, s2_raw, mean)
    s2 = (safe - mean) / (std + statistics["epsilon"])
    s2[~s2_valid] = 0.0
    tensor = np.concatenate([s1, s2], axis=0).astype(np.float32)
    if not np.isfinite(tensor).all():
        raise InputError("The preprocessed images contain invalid values.")
    return Pair(identity, tensor, s1_raw, s2_raw, valid, profile)
