"""Load the fixed Fast-SCNN checkpoint once and predict a tile in four patches."""
import hashlib
import json
import os
from pathlib import Path
import threading
import time

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch

from .model import FastSCNNDetailRefinement


ROOT = Path(os.environ.get("APP_ROOT", Path(__file__).resolve().parents[1]))


class Predictor:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.info = json.loads((self.root / "models/model_info.json").read_text())
        stats_path = self.root / "models/s2_normalization_stats.json"
        self.statistics = json.loads(stats_path.read_text())
        if hashlib.sha256(stats_path.read_bytes()).hexdigest() != self.info["normalization_sha256"]:
            raise RuntimeError("Fast-SCNN normalization file checksum does not match the selected checkpoint.")
        checkpoint = self.root / "models/fastscnn_a6_seed42.pth"
        if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != self.info["checkpoint_sha256"]:
            raise RuntimeError("Fast-SCNN checkpoint checksum mismatch.")
        torch.set_num_threads(int(os.environ.get("TORCH_THREADS", "6")))
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        self.model = FastSCNNDetailRefinement(in_channels=15, num_classes=1)
        self.model.load_state_dict(state, strict=True)
        if sum(p.numel() for p in self.model.parameters()) != self.info["parameter_count"]:
            raise RuntimeError("Fast-SCNN parameter count does not match the bundled metadata.")
        self.model.to(self.device).eval()
        self.lock = threading.Lock()

    def predict(self, pair):
        probability = np.empty((512, 512), dtype=np.float32)
        with self.lock, torch.inference_mode():
            if self.device.type == "cuda":
                torch.cuda.synchronize()
                torch.cuda.reset_peak_memory_stats(self.device)
            started = time.perf_counter()
            for row in (0, 256):
                for col in (0, 256):
                    patch = np.ascontiguousarray(pair.tensor[:, row:row + 256, col:col + 256])
                    tensor = torch.from_numpy(patch)[None].to(self.device)
                    logits = self.model(tensor)
                    probability[row:row + 256, col:col + 256] = torch.sigmoid(logits)[0, 0].cpu().numpy()
            if self.device.type == "cuda":
                torch.cuda.synchronize()
            elapsed = (time.perf_counter() - started) * 1000
            memory_mb = torch.cuda.max_memory_allocated(self.device) / 1_000_000 if self.device.type == "cuda" else None
        if not np.isfinite(probability).all():
            raise RuntimeError("Fast-SCNN produced nonfinite predictions.")
        mask = (probability > self.info["threshold"]).astype(np.uint8)
        mask[~pair.valid] = 255
        return mask, elapsed, memory_mb
