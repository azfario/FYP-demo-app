"""Separate predicted water using the bundled Sen1Floods11 JRC references."""
import base64
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import ImageColor
import rasterio
from rasterio.io import MemoryFile

from .visualization import png_url

PERMANENT_COLOR = ImageColor.getrgb('#435ee5')
FLOOD_COLOR = ImageColor.getrgb('#f59e42')
SOURCE = 'Sen1Floods11 v1.1 JRCWaterHand; EC JRC/Google'
LIMITATION = 'Candidate floodwater excludes JRC permanent water; seasonal water and prediction errors may remain.'


def load_reference(pair, root):
    """Treat unavailable references as a separation failure, not an inference failure."""
    folder = Path(root) / 'references/jrc'
    try:
        manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
        if not isinstance(manifest, dict) or not isinstance(manifest.get('tiles'), dict):
            raise ValueError('Invalid JRC manifest.')
        entry = manifest['tiles'].get(pair.tile_id)
        if entry is None:
            return None, {'available': False, 'reason': 'No bundled JRC reference for this tile.'}
        # Construct the path from a validated tile identity, never from manifest paths.
        filename = f'{pair.tile_id}_JRCWaterHand.tif'
        if Path(filename).name != filename or '\\' in filename:
            raise ValueError('Invalid tile identity.')
        path = folder / filename
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('JRC reference checksum mismatch.')
        with rasterio.open(path) as src:
            if src.driver != 'GTiff' or src.count != 1 or src.shape != pair.valid.shape:
                raise ValueError('JRC reference dimensions or format do not match.')
            if src.crs != pair.profile['crs'] or not src.transform.almost_equals(pair.profile['transform'], precision=1e-9):
                raise ValueError('JRC reference geographic alignment does not match.')
            values = src.read(1)
            valid = (src.read_masks(1) > 0) & np.isfinite(values)
            if not np.isin(values[valid], [0, 1]).all():
                raise ValueError('JRC reference must contain binary values 0 and 1.')
        valid &= pair.valid
        if not valid.any():
            raise ValueError('No jointly valid JRC and satellite pixels.')
        reference = np.full(values.shape, 255, dtype=np.uint8)
        reference[valid] = values[valid]
        display = np.zeros((*values.shape, 3), dtype=np.uint8)
        display[reference == 1] = PERMANENT_COLOR
        display[~valid] = (120, 120, 120)
        info = {'available': True, 'source': SOURCE, 'filename': filename,
                'sha256': entry['sha256'], 'encoding': '0=outside permanent reference, 1=permanent water',
                'limitation': LIMITATION, 'historical_reference': True,
                'reference_png': png_url(display)}
        return reference, info
    except (OSError, ValueError, KeyError, TypeError, rasterio.errors.RasterioError):
        return None, {'available': False, 'reason': 'The bundled JRC reference is missing, invalid or geographically mismatched.'}


def classify_water(prediction, reference, imagery_valid):
    valid = imagery_valid & np.isin(prediction, [0, 1]) & np.isin(reference, [0, 1])
    classes = np.full(prediction.shape, 255, dtype=np.uint8)
    classes[valid] = 0
    classes[valid & (prediction == 1) & (reference == 1)] = 1
    classes[valid & (prediction == 1) & (reference == 0)] = 2
    return classes


def export_raster(pair, values, description, classes, provenance):
    profile = {key: pair.profile[key] for key in ('crs', 'transform', 'height', 'width')}
    profile.update(driver='GTiff', count=1, dtype='uint8', nodata=255, compress='deflate')
    with MemoryFile() as memory:
        with memory.open(**profile) as dst:
            dst.write(values, 1)
            dst.set_band_description(1, description)
            dst.update_tags(classes=classes, source=SOURCE, reference_sha256=provenance['sha256'],
                            reference_filename=provenance['filename'], method='predicted water intersected with binary JRC reference',
                            threshold='probability > 0.5', model='D4 seed 2026', limitation=LIMITATION)
        return base64.b64encode(memory.read()).decode()


def separation_result(pair, prediction, root):
    reference, info = load_reference(pair, root)
    if reference is None:
        return info
    classes = classify_water(prediction, reference, pair.valid)
    layer = np.zeros((*classes.shape, 4), dtype=np.uint8)
    layer[classes == 1] = (*PERMANENT_COLOR, 255)
    layer[classes == 2] = (*FLOOD_COLOR, 255)
    layer[classes == 255] = (120, 120, 120, 255)
    candidate = np.where(classes == 2, 1, 0).astype(np.uint8)
    candidate[classes == 255] = 255
    return {**info, 'overlay_layer': png_url(layer),
            'counts': {'detected_permanent_water': int((classes == 1).sum()),
                       'candidate_floodwater': int((classes == 2).sum()),
                       'excluded': int((classes == 255).sum())},
            'classes_geotiff_base64': export_raster(pair, classes, 'water_types',
                '0=background, 1=detected permanent water, 2=candidate floodwater, 255=no data', info),
            'candidate_flood_geotiff_base64': export_raster(pair, candidate, 'candidate_floodwater',
                '0=not candidate floodwater, 1=candidate floodwater, 255=no data', info)}
