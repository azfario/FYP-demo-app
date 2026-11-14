"""Regenerate the CPU fixture from the original A6 snapshot and training checkpoint."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import runpy

import numpy as np
import rasterio
import torch
from torch import nn
from torch.nn import functional as F


def generate(a6):
    snapshot = a6 / "snapshots"
    notebook = snapshot / "baseline_fastscnn.ipynb"
    checkpoint = a6 / "trials/trial_007_ae3777ebbeaa/best_finetuned.pth"
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == "bc2d793b9bae75d282869555290fee0ce809fc758e38a497bbbc46dceb434d46"
    cells = json.loads(notebook.read_text(encoding="utf8"))["cells"]
    namespace = dict(torch=torch, nn=nn, F=F, np=np, rasterio=rasterio, Dataset=torch.utils.data.Dataset)
    for index in (7, 9):
        definitions = ast.parse("".join(cells[index]["source"]))
        definitions.body = [node for node in definitions.body if isinstance(node, ast.ClassDef)]
        exec(compile(definitions, str(notebook), "exec"), namespace)
    torch.set_num_threads(4)
    model = namespace["FastSCNNDetailRefinement"]().eval()
    model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True)["model_state"], strict=True)
    folder = Path(__file__).resolve().parents[2] / "sample/bolivia 1"
    s1, s2 = sorted(folder.glob("*.tif"))
    dataset = namespace["Sen1FloodsFusionDataset"].__new__(namespace["Sen1FloodsFusionDataset"])
    radar = dataset._preprocess_s1(dataset._read_tif(s1))
    stats = json.loads((snapshot / "s2_normalization_stats.json").read_text())
    optical = runpy.run_path(str(snapshot / "s2_normalization.py"))["standardize_s2_raster"](s2, stats)
    tensor = torch.from_numpy(np.concatenate([radar, optical]))[None]
    with torch.inference_mode():
        center = model(tensor[:, :, 128:384, 128:384].contiguous()).numpy()
        strips = [torch.cat([model(p.contiguous()) for p in row.chunk(2, dim=3)], dim=3)
                  for row in tensor.chunk(2, dim=2)]
        mask = (torch.cat(strips, dim=2).sigmoid()[0, 0].numpy() > 0.5).astype(np.uint8)
    with rasterio.open(s1) as a, rasterio.open(s2) as b:
        valid = ((a.read_masks() > 0) & np.isfinite(a.read())).all(0)
        valid &= ((b.read_masks() > 0) & np.isfinite(b.read())).any(0)
    mask[~valid] = 255
    np.savez_compressed(Path(__file__).with_name("a6_seed42_reference.npz"), center_logits=center,
                        full_mask=mask, input_sha256=hashlib.sha256(tensor.numpy().tobytes()).hexdigest())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("a6", type=Path)
    generate(parser.parse_args().a6)
