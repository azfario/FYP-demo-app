"""Copy the ten selected demonstration triplets from an original Sen1Floods11 tree."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil

SELECTION = [
    ("India_900498", "Broad braided river channels and contrasting exposed islands."),
    ("India_399883", "Connected water channels around large river islands."),
    ("India_747992", "Extensive irregular water coverage across the floodplain."),
    ("India_591317", "Wide muddy-water boundary adjoining vegetated land."),
    ("Nigeria_812045", "Broad inundated corridor with visible vegetation boundaries."),
    ("Spain_7387658", "Large fragmented labelled-water pattern across agricultural parcels."),
    ("Spain_7370579", "Detailed branching labelled-water pattern around land parcels."),
    ("Paraguay_1029191", "Wide river channel with secondary floodplain water features."),
    ("Paraguay_790830", "Distinct river bend and connected narrow water channels."),
    ("Somalia_322855", "Irregular labelled floodplain water contrasting with nearby dry land."),
]


def prepare(source, destination):
    splits = {}
    for name in ("test", "train", "valid"):
        path = source / f"splits/flood_handlabeled/flood_{name}_data.csv"
        with path.open(newline="") as stream:
            splits[name] = {row[0].removesuffix("_S1Hand.tif") for row in csv.reader(stream)}
    manifest = {"dataset": "Sen1Floods11 v1.1", "source_split": "flood_test_data.csv",
                "source_split_sha256": hashlib.sha256((source / "splits/flood_handlabeled/flood_test_data.csv").read_bytes()).hexdigest(),
                "selection": "Visual inspection of water/land patterns, not model prediction scores. Selected demonstrations, not a representative benchmark of all 90 Hand Test tiles.",
                "label_values": {"0": "background", "1": "water", "-1": "ignored", "255": "ignored"}, "samples": []}
    for index, (tile, reason) in enumerate(SELECTION, 1):
        assert tile in splits["test"] and tile not in splits["train"] | splits["valid"], tile
        folder = f"hand test {index}"
        target = destination / folder
        target.mkdir(parents=True, exist_ok=True)
        entry = {"id": index, "folder": folder, "tile_id": tile, "split": "Hand Test",
                 "in_training_split": False, "in_validation_split": False, "selection_reason": reason, "files": {}}
        for key, kind in (("s1", "S1Hand"), ("s2", "S2Hand"), ("ground_truth", "LabelHand")):
            filename = f"{tile}_{kind}.tif"
            original = source / "data/flood_events/HandLabeled" / kind / filename
            checksum = hashlib.sha256(original.read_bytes()).hexdigest()
            output = target / filename
            if output.exists() and hashlib.sha256(output.read_bytes()).hexdigest() != checksum:
                raise ValueError(f"Refusing to overwrite a changed file: {output}")
            shutil.copyfile(original, output)
            assert hashlib.sha256(output.read_bytes()).hexdigest() == checksum
            entry["files"][key] = {"filename": filename, "sha256": checksum, "bytes": output.stat().st_size}
        manifest["samples"].append(entry)
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Copied {len(SELECTION)} triplets (30 unchanged TIFFs) to {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Original Sen1Floods11 v1.1 directory")
    args = parser.parse_args()
    prepare(args.source, Path(__file__).resolve().parents[1] / "hand test")
