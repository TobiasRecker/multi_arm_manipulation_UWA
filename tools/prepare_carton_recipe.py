#!/usr/bin/env python3
"""Freeze hardware carton geometry and a versioned, object-relative contact design.

Pure offline data preparation: no Gazebo, ROS context, drivers or device calls.
Never depend on a previous simulation run's removable collision directory.
"""
import argparse
import fcntl
import hashlib
from importlib.util import find_spec
import json
import math
from pathlib import Path
import re
import sys
import tempfile

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
    optional_fields = {'object_to_tool0', 'entry_inward_shift_m', 'contact_model'}
    if not isinstance(design, dict) or not design_fields <= set(design) or set(design)-design_fields-optional_fields:
        raise ValueError("Invalid carton program contact design")
    if set(design) & optional_fields:
        from match_cooperative_handling.rigid_object import rigid
        if (not optional_fields <= set(design) or design['entry_inward_shift_m'] != 0.
                or design['contact_model'] != 'physical_skin_and_outer_hull'
                or not isinstance(design['object_to_tool0'], dict)
                or set(design['object_to_tool0']) != {'right_front', 'right_rear'}):
            raise ValueError('Exact simulation grips require both rigid offsets, zero entry shift and physical skin contact')
        for transform in design['object_to_tool0'].values():
            rigid(transform)
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


def file_sha(path):
    with path.open("rb") as data:
        return hashlib.file_digest(data, "sha256").hexdigest()


def validated_asset(asset, definition):
    manifest = json.loads((asset / "asset.json").read_text())
    if (manifest["asset_id"], manifest["version"]) != (definition["asset_id"], definition["asset_version"]):
        raise ValueError(f"This recipe requires {definition['asset_id']} version {definition['asset_version']}")
    for name, digest in manifest["files"].items():
        if file_sha(asset / name) != digest:
            raise ValueError("Asset changed: " + name)
    return manifest


def prepare(asset, output, config_path, inventory, program=None):
    from uwa_cell_tasks.scene import carton_shapes
    from uwa_cell_motion.common import config
    from uwa_cell_motion.hardware_model import HardwareProblem

    definition = load_program(DEFAULT_PROGRAM) if program is None else program
    design = definition["contact_design"]
    asset = asset.resolve()
    output = output.resolve()
    manifest = validated_asset(asset, definition)

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
    for key in ('object_to_tool0', 'entry_inward_shift_m', 'contact_model'):
        if key in design:
            candidate[key] = design[key]
    contact_design = dict(schema_version=1, candidate=candidate,
                          scope="Nominal end-wall recipe; current camera pose and actual open-jaw alignment still required",
                          force_raw=0, speed_raw=16, mass_kg_user_reported=.5, wall_force_reference_n_user_reported=50.,
                          reference_scope="50N per jaw/wall patch, not a measured failure threshold")
    (output / "contacts.json").write_text(json.dumps(contact_design, indent=2) + "\n")

    model = HardwareProblem(output / "model", config(config_path), inventory)
    (output / "hardware.urdf").write_text(model.original_description)
    if program is not None:
        (output / "program.json").write_text(json.dumps(program, indent=2, allow_nan=False) + "\n")
    return dict(scene=str(output / "scene.json"), contacts=str(output / "contacts.json"),
                description=str(output / "hardware.urdf"), model_signature=model.signature,
                shapes=len(shapes), device_commands=[])


def cache_inputs(asset, config_path, inventory, program):
    from ament_index_python.packages import get_package_share_directory
    import cv2
    from match_ur_hardware.profiles import load_profiles
    import numpy
    import scipy
    from uwa_cell_description.configuration import load_layout

    if load_program(program["program_id"]) != program:
        raise ValueError("The named carton program changed during preparation. Retry the preparation.")
    manifest = validated_asset(asset, program)
    paths = {Path(__file__), config_path, inventory, asset / "asset.json",
             PROGRAM_DIRECTORY / (program["program_id"] + ".json")}
    paths.update(asset / name for name in manifest["files"])
    paths.update(Path(profile["kinematics_file"]) for profile in load_profiles(inventory).values()
                 if profile["kinematics_file"])
    for package in ("uwa_cell_description", "ur_description"):
        share = Path(get_package_share_directory(package))
        for directory in ("config", "urdf", "meshes"):
            paths.update(path for path in (share / directory).rglob("*", recurse_symlinks=True) if path.is_file())
    for module in (
        "match_ur_hardware.profiles", "uwa_cell_tasks.scene", "uwa_cell_description.configuration",
        "uwa_cell_description.calibration_profile", "uwa_cell_description.overview_profile",
        "uwa_cell_gazebo.configuration", "uwa_cell_gazebo.charuco", "uwa_cell_motion.common",
        "uwa_cell_motion.hardware_model", "uwa_cell_motion.geometry", "uwa_cell_control.scan_separation",
        "uwa_cell_control.view_geometry", "uwa_cell_control.parallel_scan", "uwa_cell_calibration.model",
    ):
        paths.add(Path(find_spec(module).origin))
    for module in ("xacro", "yaml"):
        paths.update(Path(find_spec(module).origin).parent.glob("*.py"))
    return {
        "files": {str(path.absolute()): file_sha(path) for path in sorted(paths)},
        "layout": load_layout(),
        "program": program,
        "versions": [sys.version, numpy.__version__, scipy.__version__, cv2.__version__],
    }


def cached_recipe(asset, config_path, inventory, program, cache):
    from uwa_cell_tasks.core import digest, seal, verify, write_json

    cache, asset = cache.resolve(), asset.resolve()
    config_path, inventory = config_path.resolve(), inventory.resolve()
    key = digest(cache_inputs(asset, config_path, inventory, program))
    entry = cache / key
    entry.mkdir(parents=True, exist_ok=True)
    if entry.is_symlink():
        raise ValueError("The static recipe identity directory must be local to its cache")
    receipt_path = entry / "receipt.json"
    with (entry / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cached = None
        if receipt_path.is_file():
            try:
                receipt = verify(json.loads(receipt_path.read_text()))
                output = (entry / receipt["generation"]).resolve()
                files = receipt["files"]
                required = {"contacts.json", "hardware.urdf", "program.json", "scene.json"}
                if (receipt["cache_key"] == key and output.parent.parent == entry
                        and output.parent.name.startswith("build-") and output.name == "recipe"
                        and isinstance(files, dict)
                        and required <= files.keys()
                        and all((output / name).resolve().is_relative_to(output)
                                and file_sha(output / name) == sha for name, sha in files.items())):
                    cached = dict(receipt["result"], recipe=str(output), cache_hit=True, cache_key=key)
            except (OSError, ValueError, KeyError, TypeError):
                pass
        if cached is not None:
            if digest(cache_inputs(asset, config_path, inventory, program)) != key:
                raise ValueError("The static recipe inputs changed while reading the cache. Retry the preparation.")
            return cached

        # URDF and scene files contain absolute paths. Give each build its
        # final location before rendering and publish only the small receipt.
        output = Path(tempfile.mkdtemp(prefix="build-", dir=entry)) / "recipe"
        result = prepare(asset, output, config_path, inventory, program=program)
        if digest(cache_inputs(asset, config_path, inventory, program)) != key:
            raise ValueError("The static recipe inputs changed while building. Retry the preparation.")
        files = {path.relative_to(output).as_posix(): file_sha(path)
                 for path in sorted(output.rglob("*")) if path.is_file()}
        write_json(receipt_path, seal(dict(cache_key=key, generation=str(output.relative_to(entry)), files=files,
                                           result=result)))
        return dict(result, recipe=str(output), cache_hit=False, cache_key=key)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", type=Path, default=DEFAULT_ASSET)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", type=Path)
    destination.add_argument("--cache-dir", type=Path, help="Reuse a hash-bound static recipe on this host")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--program", help=f"Named carton program (default recipe: {DEFAULT_PROGRAM})")
    args = parser.parse_args()
    try:
        program = load_program(args.program) if args.program is not None else None
        if args.cache_dir is None:
            result = prepare(args.asset, args.output, args.config, args.inventory, program=program)
        else:
            result = cached_recipe(args.asset, args.config, args.inventory, program or load_program(DEFAULT_PROGRAM),
                                   args.cache_dir)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))
