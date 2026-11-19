"""Prepare the current P2S MuJoCo model as an isolated CUDA-training source.

The CUDA trainer expects ``robot_dog_v2.xml`` and an ``assets`` directory in a
single source folder.  The P2S preview keeps its chassis beside its XML and
shares the historical leg meshes one directory up, so this script makes an
explicit, portable copy without changing either original model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
P2S = ROOT / "simulation" / "mujoco" / "p2s"
ASSETS = ROOT / "simulation" / "mujoco" / "assets"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare(output: Path, replace: bool = False) -> None:
    if output.exists():
        if not replace:
            raise FileExistsError(f"Output already exists: {output} (use --replace to rebuild it)")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    asset_out = output / "assets"
    shutil.copytree(ASSETS, asset_out)
    shutil.copy2(P2S / "chassis.stl", output / "chassis.stl")

    tree = ET.parse(P2S / "robot_dog_p2s.xml")
    root = tree.getroot()
    root.set("model", "Luca P2S quasi-static crawl training source")
    root.find("compiler").set("meshdir", ".")
    for mesh in root.findall("asset/mesh"):
        filename = mesh.get("file", "")
        if filename.startswith("../assets/"):
            mesh.set("file", "assets/" + filename.removeprefix("../assets/"))
    ET.indent(root)
    model_out = output / "robot_dog_v2.xml"
    tree.write(model_out, encoding="utf-8", xml_declaration=True)

    required = [output / "chassis.stl", model_out, *asset_out.glob("*.stl")]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("Prepared source is incomplete: " + ", ".join(missing))
    manifest = {
        "status": "prepared_for_simulation_only",
        "source_model": str((P2S / "robot_dog_p2s.xml").resolve()),
        "source_model_sha256": sha256(P2S / "robot_dog_p2s.xml"),
        "prepared_model_sha256": sha256(model_out),
        "chassis_sha256": sha256(output / "chassis.stl"),
        "limitations": [
            "P2S mass and inertia are provisional.",
            "The final battery, Pi, PDB and enclosure locations are not modeled as final hardware.",
            "This source is for slow simulation training; it does not authorize unsupported hardware walking.",
        ],
    }
    (output / "p2s-training-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    prepare(args.output.resolve(), args.replace)


if __name__ == "__main__":
    main()
