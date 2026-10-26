"""Display stretches are separate from the model's input preprocessing."""
import base64
from io import BytesIO

import cv2
import numpy as np
from PIL import Image
from rasterio.io import MemoryFile

OVERLAY_COLOR = (67, 94, 229)


def png_bytes(array, size=None):
    image = Image.fromarray(array)
    if size:
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def png_url(array):
    return "data:image/png;base64," + base64.b64encode(png_bytes(array)).decode()


def stretch(channel, valid):
    usable = valid & np.isfinite(channel)
    result = np.zeros(channel.shape, dtype=np.uint8)
    if usable.any():
        low, high = np.percentile(channel[usable], [2, 98])
        if high > low:
            values = np.nan_to_num(channel, nan=low, posinf=high, neginf=low)
            result = (np.clip((values - low) / (high - low), 0, 1) * 255).astype(np.uint8)
    return result


def previews(pair):
    rgb = np.stack([stretch(pair.s2_raw[i], pair.valid) for i in (3, 2, 1)], axis=-1)
    rgb[~pair.valid] = (230, 230, 226)
    radar = stretch(pair.s1_raw[0], pair.valid)
    radar[~pair.valid] = 120
    return rgb, radar


def result_images(pair, mask, opacity=0.5):
    rgb, radar = previews(pair)
    foreground = (mask == 1) & pair.valid
    binary = np.where(mask == 1, 255, 0).astype(np.uint8)
    binary[~pair.valid] = 120
    layer = np.zeros((*mask.shape, 4), dtype=np.uint8)
    layer[foreground] = (*OVERLAY_COLOR, 255)
    tinted = np.empty_like(rgb)
    tinted[:] = OVERLAY_COLOR
    blended = cv2.addWeighted(rgb, 1 - opacity, tinted, opacity, 0)
    overlay = rgb.copy()
    overlay[foreground] = blended[foreground]
    return {"rgb": png_url(rgb), "radar": png_url(radar), "mask": png_url(binary),
            "overlay_layer": png_url(layer), "overlay": png_url(overlay)}


def geotiff_base64(pair, mask):
    profile = {key: pair.profile[key] for key in ("crs", "transform", "height", "width")}
    profile.update(driver="GTiff", count=1, dtype="uint8", nodata=255, compress="deflate")
    with MemoryFile() as memory:
        with memory.open(**profile) as dst:
            dst.write(mask, 1)
            dst.set_band_description(1, "predicted_water")
            dst.update_tags(model="D4 seed 2026", threshold="probability > 0.5",
                            classes="0=background, 1=predicted water, 255=no data")
        return base64.b64encode(memory.read()).decode()
