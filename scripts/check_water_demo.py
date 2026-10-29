"""Verify all ten paired demos through a running API and inspect exported pixels."""
import argparse
import base64
import json
from pathlib import Path
import urllib.request
import uuid

import numpy as np
import rasterio
from rasterio.io import MemoryFile

ROOT = Path(__file__).resolve().parents[1]


def post(base, endpoint, files):
    boundary = uuid.uuid4().hex
    parts = []
    for field, path in files.items():
        parts.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{path.name}"\r\nContent-Type: image/tiff\r\n\r\n'.encode(),
                      path.read_bytes(), b'\r\n'])
    parts.append(f'--{boundary}--\r\n'.encode())
    request = urllib.request.Request(f'{base}/api/{endpoint}', data=b''.join(parts),
                                     headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def raster(encoded):
    with MemoryFile(base64.b64decode(encoded)) as memory, memory.open() as src:
        return src.read(1), src.profile, src.tags()


def verify(base):
    manifest = json.loads((ROOT / 'demo pairs/manifest.json').read_text())
    report = []
    for entry in manifest['samples']:
        files = {key: ROOT / 'demo pairs' / entry['folder'] / file['filename']
                 for key, file in entry['files'].items()}
        result = post(base, 'predict', files)
        separation = result['water_separation']
        assert separation['available'], separation
        water, profile, _ = raster(result['mask_geotiff_base64'])
        types, types_profile, tags = raster(separation['classes_geotiff_base64'])
        flood, flood_profile, _ = raster(separation['candidate_flood_geotiff_base64'])
        with rasterio.open(ROOT / 'references/jrc' / separation['filename']) as src:
            permanent = src.read(1)
        expected = np.where(water == 255, 255, np.where(water == 0, 0, np.where(permanent == 1, 1, 2)))
        np.testing.assert_array_equal(types, expected)
        np.testing.assert_array_equal(flood, np.where(types == 255, 255, types == 2))
        for exported in (types_profile, flood_profile):
            assert exported['crs'] == profile['crs'] and exported['transform'] == profile['transform']
            assert exported['nodata'] == 255 and (exported['height'], exported['width']) == (512, 512)
        assert tags['reference_sha256'] == separation['sha256']
        assert separation['counts']['candidate_floodwater'] == int((types == 2).sum())
        assert separation['counts']['detected_permanent_water'] == int((types == 1).sum())
        report.append({'tile_id': entry['tile_id'], 'folder': entry['folder'], 'counts': separation['counts']})
        print(f"PASS {entry['folder']} {entry['tile_id']}: {separation['counts']}")
    output = ROOT / 'test-results/water-demo-report.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:5173')
    verify(parser.parse_args().base_url.rstrip('/'))
