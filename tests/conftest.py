import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.inference import Predictor
from backend.main import app
from backend.preprocessing import read_pair

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def service():
    with patch("torch.cuda.is_available", return_value=False):
        return Predictor(ROOT)


@pytest.fixture(scope="session")
def records():
    return json.loads((ROOT / "sample/manifest.json").read_text())


@pytest.fixture
def sample_files(records):
    item = records[0]
    folder = ROOT / "sample" / item["folder"]
    return item, (folder / item["s1"]).read_bytes(), (folder / item["s2"]).read_bytes()


@pytest.fixture
def pair(sample_files, service):
    item, a, b = sample_files
    return read_pair(a, b, item["s1"], item["s2"], service.statistics)


@pytest.fixture
def client(service):
    # Lifespan startup is separately tested; reuse the fixed CPU model for API cases.
    app.state.predictor = service
    app.state.load_error = None
    return TestClient(app)
