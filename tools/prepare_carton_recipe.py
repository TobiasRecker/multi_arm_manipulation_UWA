#!/usr/bin/env python3
"""Freeze hardware carton geometry and a versioned, object-relative contact design.

Pure offline data preparation: no Gazebo, ROS context, drivers or device calls.
Never depend on a previous simulation run's removable collision directory.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[1]
PROGRAM_DIRECTORY = REPO / "config/carton_programs"
DEFAULT_PROGRAM = "carton-supported-v1"
DEFAULT_ASSET = REPO / "uwa_cell_description/assets/carton_avocado_v1"
DEFAULT_INVENTORY = REPO / "config/hardware_inventory.yaml"
DEFAULT_CONFIG = REPO / "uwa_cell_motion/config/hardware_carton_supported_trend.yaml"
sys.path.insert(0, str(REPO / "uwa_cell_tasks"))


def load_program(name):
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError("Invalid carton program name")
    path = PROGRAM_DIRECTORY / f"{name}.json"
    if not path.is_file():
        raise ValueError(f"Unknown carton program: {name}")
    program = json.loads(path.read_text())
    fields = {"schema_version", "program_id", "task", "asset_id", "asset_version", "pregrasp_m", "contact_design"}
    if not isinstance(program, dict) or set(program) != fields:
        raise ValueError("Invalid carton program fields")
    if (type(program["schema_version"]) is not int or program["schema_version"] != 1
            or program["program_id"] != name or program["task"] != "carton_supported_grasp"):
        raise ValueError("Unsupported carton program schema or task")
    if (program["asset_id"] != "carton_avocado_v1"
            or type(program["asset_version"]) is not int or program["asset_version"] != 1):
        raise ValueError("Unsupported carton program asset")
    height = program["pregrasp_m"]
    if type(height) not in (int, float) or height != 0.15:
        raise ValueError("The supported carton entry requires a 150 mm pregrasp separation")

    design = program["contact_design"]
    design_fields = {"depth_below_continuous_wall_top_m", "elbow_signs", "preferred_ik_seeds", "seed_origin", "posture_reason"}
    if not isinstance(design, dict) or set(design) != design_fields:
        raise ValueError("Invalid carton program contact design")
    depth = design["depth_below_continuous_wall_top_m"]
    if type(depth) not in (int, float) or not math.isfinite(depth) or depth <= 0:
        raise ValueError("Contact depth must be finite and positive")
    members = {"right_front", "right_rear"}
    signs = design["elbow_signs"]
    if (not isinstance(signs, dict) or not signs.keys() <= members
            or any(type(sign) is not int or sign not in (-1, 1) for sign in signs.values())):
        raise ValueError("Invalid elbow signs for the right arms")
    seeds = design["preferred_ik_seeds"]
    if (not isinstance(seeds, dict) or set(seeds) != members
            or any(not isinstance(seed, list) or len(seed) != 6
                   or any(type(joint) not in (int, float) or not math.isfinite(joint) for joint in seed)
                   for seed in seeds.values())):
        raise ValueError("Six finite IK seed values are required for each right arm")
    if any(not isinstance(design[key], str) or not design[key].strip()
           for key in ("seed_origin", "posture_reason")):
        raise ValueError("Provide the IK seed origin and posture rationale")
    return program


def prepare(asset, output, config_path, inventory, program=None):
    from uwa_cell_tasks.scene import carton_shapes
    from uwa_cell_motion.common import config
    from uwa_cell_motion.hardware_model import HardwareProblem

    definition = load_program(DEFAULT_PROGRAM) if program is None else program
    design = definition["contact_design"]
    asset = asset.resolve()
    output = output.resolve()
    manifest = json.loads((asset / "asset.json").read_text())
    if (manifest["asset_id"], manifest["version"]) != (definition["asset_id"], definition["asset_version"]):
        raise ValueError(f"This recipe requires {definition['asset_id']} version {definition['asset_version']}")
    for name, digest in manifest["files"].items():
        if hashlib.sha256((asset / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Asset changed: " + name)

    output.mkdir(parents=True, exist_ok=False)
    thickness = manifest["quality"]["wall_thickness_m"]
    shapes = carton_shapes(dict(mesh_file=asset / manifest["visual_mesh"], manifest=manifest), output / "collision", thickness)
    scene = dict(schema_version=1, kind="hardware_static_carton_geometry_only", asset_id=manifest["asset_id"],
                 asset_manifest_sha256=hashlib.sha256((asset / "asset.json").read_bytes()).hexdigest(),
                 asset_directory=str(asset), shapes=shapes, wall_thickness_measured=False, loaded_motion=False,
                 scope="Explicit task geometry proxy, no physics/force qualification")
    (output / "scene.json").write_text(json.dumps(scene, indent=2) + "\n")

    length, width, _ = manifest["dimensions_m"]
    contacts = {}
    depth = design["depth_below_continuous_wall_top_m"]
    for arm, side, x in (("right_front", 0, thickness / 2), ("right_rear", 1, length - thickness / 2)):
        top = min(shape["wall_base_top_m"] for shape in shapes
                  if shape["axis"] == 0 and shape["side"] == side and shape["wall_base_top_m"] is not None)
        if top <= depth:
            raise ValueError(f"Contact depth places {arm} at or below the carton floor")
        contacts[arm] = dict(axis=0, side=side, normal_object=[1., 0., 0.],
                             point_object=[x, width / 2, top - depth], continuous_wall_top_object_m=top)
    candidate = dict(contacts=contacts, elbow_signs=design["elbow_signs"], preferred_ik_seeds=design["preferred_ik_seeds"],
                     seed_origin=design["seed_origin"], posture_reason=design["posture_reason"])
    contact_design = dict(schema_version=1, candidate=candidate,
                          scope="Nominal end-wall recipe; current camera pose and actual open-jaw alignment still required",
                          force_raw=0, speed_raw=16, mass_kg_user_reported=.5, wall_force_reference_n_user_reported=50.,
                          reference_scope="50N per jaw/wall patch, not a measured failure threshold")
    (output / "contacts.json").write_text(json.dumps(contact_design, indent=2) + "\n")

    model = HardwareProblem(output / "model", config(config_path), inventory)
    (output / "hardware.urdf").write_text(model.original_description)
    if program is not None:
        (output / "program.json").write_text(json.dumps(program, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(scene=str(output / "scene.json"), contacts=str(output / "contacts.json"),
                          description=str(output / "hardware.urdf"), model_signature=model.signature,
                          shapes=len(shapes), device_commands=[]), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", type=Path, default=DEFAULT_ASSET)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--program", help=f"Named carton program (default recipe: {DEFAULT_PROGRAM})")
    args = parser.parse_args()
    try:
        program = load_program(args.program) if args.program is not None else None
    except ValueError as error:
        parser.error(str(error))
    prepare(args.asset, args.output, args.config, args.inventory, program=program)
