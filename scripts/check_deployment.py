"""Verify the live frontend and all ten comparison requests through Nginx."""
import base64
import hashlib
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

import numpy as np
from rasterio.io import MemoryFile

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://localhost:8081"


def upload(files, endpoint):
    boundary = "hand-test-deployment-check-20261027"
    chunks = []
    for key, (name, blob) in files.items():
        header = f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{name}"\r\nContent-Type: image/tiff\r\n\r\n'
        chunks.append(header.encode() + blob + b"\r\n")
    body = b"".join(chunks) + f"--{boundary}--\r\n".encode()
    return json.load(urlopen(Request(BASE + endpoint, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}), timeout=120))


def verify():
    html = urlopen(BASE + "/").read()
    assert html == (ROOT / "frontend/dist/index.html").read_bytes(), "The container serves a stale frontend"
    for asset in re.findall(r'(?:src|href)="(/assets/[^"]+)"', html.decode()):
        assert urlopen(BASE + asset).read() == (ROOT / "frontend/dist" / asset.lstrip("/")).read_bytes(), asset
    assert hashlib.sha256(urlopen(BASE + "/satellite-background.png").read()).hexdigest() == "369dbce74276e08360f97298259ebb9fb9ad3f30b410a022b5b6aee105fac577"
    assert json.load(urlopen(BASE + "/api/health"))["model_ready"]
    info = json.load(urlopen(BASE + "/api/model-info"))
    saved = json.loads((ROOT / "models/model_info.json").read_text())
    assert all(info[key] == value for key, value in saved.items())
    records = json.loads((ROOT / "hand test/manifest.json").read_text())["samples"]
    results = []
    for item in records:
        files = {key: (entry["filename"], (ROOT / "hand test" / item["folder"] / entry["filename"]).read_bytes()) for key, entry in item["files"].items()}
        preview = upload(files, "/api/hand-test/preview")
        assert preview["ground_truth"].startswith("data:image/png;base64,")
        result = upload(files, "/api/hand-test/predict")
        assert result["width"] == result["height"] == 512
        with MemoryFile(base64.b64decode(result["mask_geotiff_base64"])) as mem, mem.open() as src:
            pred = src.read(1)
        with MemoryFile(files["ground_truth"][1]) as mem, mem.open() as src:
            truth = src.read(1)
        valid = np.isin(truth, [0, 1]) & (pred != 255)
        p, t = pred[valid] == 1, truth[valid] == 1
        overlap, union = np.logical_and(p, t).sum(), np.logical_or(p, t).sum()
        expected = {"iou": float(overlap / union), "dice": float(2 * overlap / (p.sum() + t.sum())), "pixel_accuracy": float(np.mean(p == t))}
        for key, value in expected.items():
            assert abs(result["evaluation"][key] - value) < 1e-12
        assert result["evaluation"]["evaluated_pixels"] == int(valid.sum())
        results.append({"tile_id": item["tile_id"], "device": result["device"], **result["evaluation"]})
        print(item["tile_id"], "PASS", {key: round(value, 6) for key, value in expected.items()}, flush=True)
    (ROOT / "test-results/deployment-hand-test.json").write_text(json.dumps(results, indent=2) + "\n")
    print("PASS: served frontend matches production build; original background/model retained; all ten triplets independently scored.")


if __name__ == "__main__":
    verify()
