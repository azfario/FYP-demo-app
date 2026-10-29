import base64
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from backend.water_separation import classify_water, load_reference, separation_result
from conftest import ROOT


def synthetic(root, values, *, transform=None, nodata=None):
    folder = root / 'references/jrc'
    folder.mkdir(parents=True, exist_ok=True)
    filename = 'Test_1_JRCWaterHand.tif'
    profile = dict(driver='GTiff', height=values.shape[0], width=values.shape[1],
                   count=1, dtype='uint8', crs='EPSG:4326', transform=from_origin(10, 20, .01, .01))
    with rasterio.open(folder / filename, 'w', **{**profile, 'transform': transform or profile['transform'], 'nodata': nodata}) as dst:
        dst.write(values, 1)
    digest = hashlib.sha256((folder / filename).read_bytes()).hexdigest()
    (folder / 'manifest.json').write_text(json.dumps({'tiles': {'Test_1': {'sha256': digest}}}))
    pair = SimpleNamespace(tile_id='Test_1', valid=np.ones(values.shape, bool), profile=profile)
    return pair, folder / filename


def decode(encoded):
    with MemoryFile(base64.b64decode(encoded)) as memory, memory.open() as src:
        return src.read(1), src.profile, src.tags()


def test_known_classes_and_unknown_pixels():
    prediction = np.array([[1, 1, 0, 0, 255, 1, 1]])
    reference = np.array([[1, 0, 1, 0, 1, 255, 0]])
    valid = np.array([[True, True, True, True, True, True, False]])
    np.testing.assert_array_equal(classify_water(prediction, reference, valid), [[1, 2, 0, 0, 255, 255, 255]])


@pytest.mark.parametrize('permanent,expected', [(0, 2), (1, 1)])
def test_empty_and_full_reference_exports(tmp_path, permanent, expected):
    pair, _ = synthetic(tmp_path, np.full((2, 3), permanent, dtype=np.uint8))
    pair.valid[0, 2] = False
    prediction = np.array([[1, 0, 1], [1, 1, 0]], dtype=np.uint8)
    result = separation_result(pair, prediction, tmp_path)
    assert result['available']
    classes, profile, tags = decode(result['classes_geotiff_base64'])
    np.testing.assert_array_equal(classes, [[expected, 0, 255], [expected, expected, 0]])
    flood, _, _ = decode(result['candidate_flood_geotiff_base64'])
    expected_flood = np.where(classes == 255, 255, classes == 2).astype(np.uint8)
    np.testing.assert_array_equal(flood, expected_flood)
    assert profile['nodata'] == 255 and profile['transform'] == pair.profile['transform']
    assert str(profile['crs']) == pair.profile['crs']
    assert tags['reference_sha256'] == result['sha256']
    assert 'candidate floodwater' in tags['classes']


@pytest.mark.parametrize('failure', ['missing_manifest', 'invalid_manifest', 'missing_tile', 'missing_file', 'checksum', 'corrupt', 'alignment', 'encoding', 'all_nodata'])
def test_unavailable_references_are_nonfatal(tmp_path, failure):
    values = np.full((2, 3), 3 if failure == 'encoding' else 0, dtype=np.uint8)
    pair, path = synthetic(tmp_path, values,
                           transform=from_origin(11, 20, .01, .01) if failure == 'alignment' else None,
                           nodata=0 if failure == 'all_nodata' else None)
    manifest = path.parent / 'manifest.json'
    if failure == 'missing_manifest':
        manifest.unlink()
    elif failure == 'invalid_manifest':
        manifest.write_text('{"tiles": []}')
    elif failure == 'missing_tile':
        pair.tile_id = 'Other_2'
    elif failure == 'missing_file':
        path.unlink()
    elif failure in ('checksum', 'corrupt'):
        path.write_bytes(b'not a raster')
        if failure == 'corrupt':
            manifest.write_text(json.dumps({'tiles': {'Test_1': {'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}}}))
    reference, info = load_reference(pair, tmp_path)
    assert reference is None and not info['available'] and info['reason']
    assert not separation_result(pair, np.ones((2, 3), np.uint8), tmp_path)['available']


def test_bundle_integrity_and_ten_demo_pairs():
    manifest = json.loads((ROOT / 'references/jrc/manifest.json').read_text())
    assert len(manifest['tiles']) == 446
    for tile, entry in manifest['tiles'].items():
        path = ROOT / 'references/jrc' / entry['filename']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
        with rasterio.open(path) as src:
            assert src.shape == (512, 512) and src.count == 1
            assert src.nodata is None and np.isin(src.read(1), [0, 1]).all()
    demos = json.loads((ROOT / 'demo pairs/manifest.json').read_text())
    assert len(demos['samples']) == 10
    assert demos['source_split'] == 'flood_test_data.csv'
    empty = []
    for item in demos['samples']:
        folder = ROOT / 'demo pairs' / item['folder']
        assert len(list(folder.iterdir())) == 2
        for entry in item['files'].values():
            blob = (folder / entry['filename']).read_bytes()
            assert hashlib.sha256(blob).hexdigest() == entry['sha256']
            assert blob == (ROOT / 'hand test' / item['hand_test_folder'] / entry['filename']).read_bytes()
        reference = ROOT / 'references/jrc' / f"{item['tile_id']}_JRCWaterHand.tif"
        with rasterio.open(reference) as jrc, rasterio.open(folder / item['files']['s1']['filename']) as s1:
            assert jrc.crs == s1.crs and jrc.transform.almost_equals(s1.transform, precision=1e-9)
            if not jrc.read(1).any():
                empty.append(item['id'])
    assert empty == [3, 7, 10]


def test_api_preserves_water_and_hand_test_evaluation(client, service):
    folder = ROOT / 'hand test/hand test 1'
    files = {key: (f'India_900498_{suffix}.tif', (folder / f'India_900498_{suffix}.tif').read_bytes(), 'image/tiff')
             for key, suffix in [('s1', 'S1Hand'), ('s2', 'S2Hand'), ('ground_truth', 'LabelHand')]}
    pair_files = {key: value for key, value in files.items() if key != 'ground_truth'}
    preview = client.post('/api/preview', files=pair_files).json()
    assert preview['water_separation']['available']
    assert 'classes_geotiff_base64' not in preview['water_separation']
    hand_preview = client.post('/api/hand-test/preview', files=files).json()
    assert hand_preview['water_separation']['sha256'] == preview['water_separation']['sha256']
    normal = client.post('/api/predict', files=pair_files).json()
    hand = client.post('/api/hand-test/predict', files=files).json()
    assert normal['mask_geotiff_base64'] == hand['mask_geotiff_base64']
    assert normal['water_separation'] == hand['water_separation']
    assert 'evaluation' not in normal and hand['evaluation']['evaluated_pixels'] > 0
    water, _, _ = decode(normal['mask_geotiff_base64'])
    separated, _, _ = decode(normal['water_separation']['classes_geotiff_base64'])
    with rasterio.open(ROOT / 'references/jrc/India_900498_JRCWaterHand.tif') as src:
        permanent = src.read(1)
    expected = np.where(water == 255, 255, np.where(water == 0, 0, np.where(permanent == 1, 1, 2)))
    np.testing.assert_array_equal(separated, expected)
    with patch('backend.main.load_reference', return_value=(None, {'available': False, 'reason': 'Test missing reference.'})), \
         patch('backend.main.separation_result', return_value={'available': False, 'reason': 'Test missing reference.'}):
        missing = client.post('/api/hand-test/predict', files=files).json()
        assert not missing['water_separation']['available']
        assert missing['mask_geotiff_base64'] == normal['mask_geotiff_base64']
        assert missing['evaluation'] == hand['evaluation']
