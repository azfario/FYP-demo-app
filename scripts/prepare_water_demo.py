"""Bundle original JRC references and ten paired demos from an existing dataset."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def copy_verified(source, destination):
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() != checksum:
        raise ValueError(f'Refusing to overwrite changed file: {destination}')
    shutil.copyfile(source, destination)
    assert hashlib.sha256(destination.read_bytes()).hexdigest() == checksum
    return {'filename': destination.name, 'sha256': checksum, 'bytes': destination.stat().st_size}


def prepare(source):
    references = ROOT / 'references/jrc'
    tiles = {}
    for path in sorted((source / 'data/flood_events/HandLabeled/JRCWaterHand').glob('*.tif')):
        satellite = path.parent.parent / 'S1Hand' / path.name.replace('_JRCWaterHand', '_S1Hand')
        with rasterio.open(path) as reference, rasterio.open(satellite) as image:
            if reference.count != 1 or reference.shape != image.shape or reference.crs != image.crs or not reference.transform.almost_equals(image.transform, precision=1e-9):
                raise ValueError(f'Reference does not match original satellite grid: {path}')
            if reference.nodata is not None or not np.isin(reference.read(1), [0, 1]).all():
                raise ValueError(f'Expected original binary JRC reference with no nodata: {path}')
        tiles[path.name.removesuffix('_JRCWaterHand.tif')] = copy_verified(path, references / path.name)
    if len(tiles) != 446:
        raise ValueError(f'Expected 446 JRC references, found {len(tiles)}')
    manifest = {'dataset': 'Sen1Floods11 v1.1', 'source': 'EC JRC/Google via Cloud to Street',
                'source_url': 'https://github.com/cloudtostreet/Sen1Floods11/blob/master/docs/README.md',
                'encoding': {'0': 'outside permanent reference', '1': 'permanent water'},
                'temporal_note': 'Historical supplied reference; exact derivation dates and threshold are not established here. Not a verified pre-event baseline.',
                'tiles': tiles}
    (references / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    hand = json.loads((ROOT / 'hand test/manifest.json').read_text(encoding='utf-8'))
    demos = []
    for sample in hand['samples']:
        folder = f"demo {sample['id']:02}"
        files = {}
        for key in ('s1', 's2'):
            filename = sample['files'][key]['filename']
            files[key] = copy_verified(ROOT / 'hand test' / sample['folder'] / filename,
                                       ROOT / 'demo pairs' / folder / filename)
        demos.append({'id': sample['id'], 'folder': folder, 'tile_id': sample['tile_id'],
                      'hand_test_folder': sample['folder'], 'files': files})
    (ROOT / 'demo pairs/manifest.json').write_text(json.dumps({
        'dataset': hand['dataset'], 'source_split': hand['source_split'],
        'source_split_sha256': hand['source_split_sha256'],
        'selection': 'Same selected Hand Test demonstrations; not selected by model scores and not a representative benchmark.',
        'samples': demos}, indent=2) + '\n', encoding='utf-8')
    print(f'Prepared {len(tiles)} references and {len(demos)} unchanged satellite pairs.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    prepare(parser.parse_args().source)
