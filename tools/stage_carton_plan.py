#!/usr/bin/env python3
"""Stage an offline carton plan at the executor's paths, before motion review."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from shutil import copyfile
import sys
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET


REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parents[1]
sys.path.insert(0, str(REPO / "uwa_cell_tasks"))

from match_ur_hardware.profiles import load_profiles
from uwa_cell_control.parallel_scan import collision_signature
from uwa_cell_motion.common import config, sha
from uwa_cell_tasks.motion_review import caps
from uwa_cell_tasks.reviewed_carton import checker_identity, file_hash


EVIDENCE = Path("high-plan/evidence.json")
COLLISION_MODEL = Path("high-plan/moveit/robot.urdf")
BASE_MODEL = Path("high-plan/model/moveit/robot.urdf")
ENTRY = Path("entry-plan/result.json")
SCENE = Path("recipe/scene.json")
CONTACTS = Path("recipe/contacts.json")
PROGRAM = Path("recipe/program.json")
HIGH_TARGET = Path("planned-high.json")


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as output:
        json.dump(data, output, allow_nan=False, separators=(",", ":"))
        output.write("\n")


def verify_file(path, expected):
    actual = file_hash(path)
    if actual != expected:
        raise ValueError(f"Carton plan source changed: {path}")
    return actual


def require_path(path):
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Expected an absolute, normalized path: {path}")
    return path


def local_file(uri):
    parsed = urlparse(uri)
    if parsed.scheme != "file" or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError(f"Unsupported mesh URI: {uri}")
    return require_path(Path(unquote(parsed.path)))


def model_binding(profiles, model, configuration):
    return sha(json.dumps(dict(inventory=profiles, model=model, config=configuration,
                               policy="all-tool-openings-v1"), sort_keys=True))


class Staging:
    def __init__(self, plan, recipe, output, target_root, target_workspace, description_share=None, description_source=None):
        self.plan = plan
        self.recipe = recipe
        self.output = output
        self.target_root = require_path(target_root)
        self.target_workspace = require_path(target_workspace)
        self.description_share = None if description_share is None else require_path(description_share)
        self.description_source = None if description_source is None else require_path(description_source)
        if not target_root.is_relative_to(target_workspace / "setup/tasks"):
            raise ValueError("Target plan must be under the executor workspace setup/tasks")
        self.resources = {}

    def copy(self, source, relative):
        destination = self.output / relative
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            copyfile(source, destination)
        return self.target_root / relative

    def target_resource(self, source):
        require_path(source)
        local_share = WORKSPACE/'install_lyrical/uwa_cell_description/share/uwa_cell_description'
        if self.description_share is not None and source.is_relative_to(local_share):
            return self.description_share/source.relative_to(local_share)
        local_source = WORKSPACE/'src/multi_arm_manipulation_UWA/uwa_cell_description'
        if self.description_source is not None and source.is_relative_to(local_source/'meshes'):
            return self.description_source/source.relative_to(local_source)
        if source.is_relative_to(WORKSPACE):
            return self.target_workspace / source.relative_to(WORKSPACE)
        if source.is_relative_to(Path("/opt/ros/lyrical")):
            return source
        raise ValueError(f"Unrecognized installed carton resource: {source}")

    def resource(self, source, expected=None):
        target = self.target_resource(source)
        digest = file_hash(source) if expected is None else verify_file(source, expected)
        self.resources[str(target)] = digest
        return target

    def uri(self, uri, *, collision=False):
        source = local_file(uri)
        if source.is_relative_to(self.recipe):
            target = self.copy(source, Path("recipe") / source.relative_to(self.recipe))
        elif source.is_relative_to(self.plan):
            target = self.copy(source, source.relative_to(self.plan))
            if source.suffix == ".dae" and source.with_suffix(".png").is_file():
                self.copy(source.with_suffix(".png"), source.with_suffix(".png").relative_to(self.plan))
        elif collision:
            target = self.resource(source)
        else:
            target = self.target_resource(source)
        return target.as_uri()

    def urdf(self, xml):
        robot = ET.fromstring(xml)
        collisions = set(robot.findall(".//collision/geometry/mesh"))
        for mesh in robot.findall(".//mesh"):
            filename = mesh.get("filename")
            if filename.startswith("file:"):
                mesh.set("filename", self.uri(filename, collision=mesh in collisions))
            elif not filename.startswith("package://"):
                raise ValueError(f"Unsupported mesh URI: {filename}")
        return ET.tostring(robot, encoding="unicode")


def stage(plan, output, target_root, target_workspace, description_share=None, description_source=None):
    workflow = read_json(plan / "workflow.json")
    if (workflow.get("phase") != "OFFLINE_APPROACH_PREPARED" or workflow.get("success") is not True
            or workflow.get("execute") is not False):
        raise ValueError("Only a successfully checked offline plan may be staged")
    checked = checker_identity(REPO / "tools")
    joint_cap, tcp_cap = caps(workflow["speed_percent"])

    evidence = read_json(plan / EVIDENCE)
    entry = read_json(plan / ENTRY)
    inputs = evidence["inputs"]
    if set(inputs) != {"observations", "object_pose", "contact_design", "contact_scene", "config", "inventory"}:
        raise ValueError("Unexpected inputs in the source plan")
    for record in inputs.values():
        verify_file(Path(record["path"]), record["sha256"])
    source_recipe = require_path(Path(inputs["contact_scene"]["path"])).parent
    program = workflow.get("program", {})
    if (Path(inputs["contact_scene"]["path"]) != source_recipe / SCENE.name
            or Path(inputs["contact_design"]["path"]) != source_recipe / CONTACTS.name
            or Path(program.get("path", "")) != source_recipe / PROGRAM.name):
        raise ValueError("Plan does not use a bound named carton recipe")
    verify_file(source_recipe / PROGRAM.name, program["sha256"])
    staging = Staging(plan, source_recipe, output, target_root, target_workspace, description_share, description_source)

    base = (plan / BASE_MODEL).read_text()
    frozen = (plan / COLLISION_MODEL).read_text()
    old_base_signature = collision_signature(base)
    if (evidence.get("model_signature") != collision_signature(frozen)
            or entry.get("base_signature") != old_base_signature):
        raise ValueError("The source plan's model signatures do not match its frozen URDFs")
    new_base_signature = collision_signature(staging.urdf(base))
    rebased_frozen = staging.urdf(frozen)
    frozen_path = output / COLLISION_MODEL
    frozen_path.parent.mkdir(parents=True, exist_ok=True)
    frozen_path.write_text(rebased_frozen)
    evidence["model_signature"] = collision_signature(rebased_frozen)

    if evidence["configuration"] != config(Path(inputs["config"]["path"])):
        raise ValueError("Source plan configuration changed")
    profiles = load_profiles(Path(inputs["inventory"]["path"]))
    old_binding = model_binding(profiles, old_base_signature, evidence["configuration"])
    for profile in profiles.values():
        profile["kinematics_file"] = str(staging.resource(Path(profile["kinematics_file"])))
    new_binding = model_binding(profiles, new_base_signature, evidence["configuration"])
    for key in ("config", "inventory"):
        record = inputs[key]
        record["path"] = str(staging.resource(Path(record["path"]), record["sha256"]))
    source = evidence["source"]
    source["path"] = str(staging.resource(Path(source["path"]), source["sha256"]))
    evidence["mesh_sha256"] = {str(staging.resource(Path(path), digest)): digest
                               for path, digest in evidence["mesh_sha256"].items()}

    scene = read_json(source_recipe / SCENE.name)
    asset = Path(scene["asset_directory"])
    scene["asset_directory"] = str(staging.resource(asset / "asset.json", scene["asset_manifest_sha256"]).parent)
    for shape in scene["shapes"]:
        mesh = local_file(shape["uri"])
        if not mesh.is_relative_to(source_recipe / "collision"):
            raise ValueError("Carton mesh must belong to the frozen recipe")
        verify_file(mesh, shape["sha256"])
        shape["uri"] = staging.uri(shape["uri"])
    write_json(output / SCENE, scene)
    staging.copy(source_recipe / PROGRAM.name, PROGRAM)
    staging.copy(source_recipe / CONTACTS.name, CONTACTS)
    staging.copy(plan / HIGH_TARGET, HIGH_TARGET)

    source_pose = Path(inputs["object_pose"]["path"])
    for key, filename in (("observations", "observations.json"), ("object_pose", "object-pose.json")):
        record = inputs[key]
        if record != workflow["offline_inputs"][key]:
            raise ValueError(f"Workflow and evidence disagree about {key}")
        record["path"] = str(staging.copy(Path(record["path"]), Path("inputs") / filename))
    inputs["contact_design"]["path"] = str(target_root / CONTACTS)
    inputs["contact_scene"] = dict(path=str(target_root / SCENE), sha256=file_hash(output / SCENE))
    write_json(output / EVIDENCE, evidence)

    entry_source = REPO / "tools/prepare_carton_open_entry.py"
    entry_files = {plan / EVIDENCE: EVIDENCE, plan / HIGH_TARGET: HIGH_TARGET,
                   source_pose: Path("inputs/object-pose.json"), source_recipe / SCENE.name: SCENE}
    old_inputs = entry["inputs"]
    if set(old_inputs) != {str(path) for path in (*entry_files, entry_source)}:
        raise ValueError("Unexpected inputs in the open-entry plan")
    for path, expected in old_inputs.items():
        verify_file(Path(path), expected)
    target_source = staging.resource(entry_source, old_inputs[str(entry_source)])
    entry["inputs"] = {str(target_root / relative): file_hash(output / relative)
                       for relative in entry_files.values()}
    entry["inputs"][str(target_source)] = old_inputs[str(entry_source)]
    entry["base_signature"] = new_base_signature
    write_json(output / ENTRY, entry)

    for phase, source_plan in (("high", EVIDENCE), ("entry", ENTRY)):
        relative = Path(f"review-{phase}.json")
        bundle = read_json(plan / relative)
        if bundle.get("schema_version") != 2 or bundle.get("phase") != phase:
            raise ValueError(f"Unsupported {phase} motion bundle")
        if bundle.get("checker") != checked:
            original = bundle.get("checker", {}).get("components", {})
            changed = (name for name, digest in checked["components"].items() if original.get(name) != digest)
            raise ValueError(f"Source {phase} bundle has a different checker: " + ", ".join(changed))
        if bundle.get("model_signature") != old_base_signature or bundle.get("hardware_binding") != old_binding:
            raise ValueError(f"Source {phase} bundle does not match its frozen model and inventory")
        if bundle.get("joint_limit_rad_s") != joint_cap or bundle.get("tcp_limit_m_s") != tcp_cap:
            raise ValueError(f"Source {phase} bundle does not match the configured planning speed")
        verify_file(plan / source_plan, bundle["source_sha256"])
        preview = Path(bundle["preview_urdf"])
        preview_relative = Path(f"prepared-{phase}/preview.urdf")
        if preview != plan / preview_relative:
            raise ValueError(f"Unexpected {phase} preview path")
        verify_file(preview, bundle["preview_urdf_sha256"])
        preview_target = staging.copy(preview, preview_relative)
        # Previews reference installed packages and have no per-host mesh URIs.
        if any(mesh.get("filename", "").startswith("file:") for mesh in ET.parse(preview).findall(".//mesh")):
            raise ValueError(f"Non-portable mesh path in {phase} preview")
        bundle.update(model_signature=new_base_signature, hardware_binding=new_binding,
                      source_sha256=file_hash(output / source_plan), preview_urdf=str(preview_target))
        write_json(output / relative, bundle)

    weighing_requested = workflow.get('weighing_requested', False)
    if weighing_requested:
        relative = Path('weigh-plan')
        proof = read_json(plan/relative/'proof.json')
        bundle = read_json(plan/relative/'review.json')
        if (not proof.get('success') or proof.get('phase') != 'OFFLINE_WEIGH_LIFT_PREPARED'
                or proof.get('height_m') != .020 or bundle.get('phase') != 'weigh'
                or bundle.get('checker') != checked or bundle.get('model_signature') != old_base_signature
                or bundle.get('hardware_binding') != old_binding
                or bundle.get('joint_limit_rad_s') != joint_cap or bundle.get('tcp_limit_m_s') != tcp_cap):
            raise ValueError('Weigh lift does not match the frozen approach, model or speed')
        verify_file(plan/relative/'proof.json', bundle['source_sha256'])
        mapping = {plan/ENTRY: ENTRY, plan/'review-entry.json': Path('review-entry.json'),
                   source_pose: Path('inputs/object-pose.json'), source_recipe/SCENE.name: SCENE}
        expected = {*map(str,mapping), str(REPO/'tools/prepare_carton_weigh.py'),
                    str(REPO/'tools/prepare_carton_open_entry.py'),
                    str(REPO/'tools/carton_weigh_phase.py'),str(REPO/'uwa_cell_tasks/uwa_cell_tasks/carton_weighing.py')}
        if set(proof['inputs']) != expected:
            raise ValueError('Unexpected weighing proof inputs')
        rebased = {}
        for name, digest in proof['inputs'].items():
            source_path = Path(name); verify_file(source_path,digest)
            if source_path in mapping:
                target = target_root/mapping[source_path]; digest = file_hash(output/mapping[source_path])
            else:
                target = staging.resource(source_path,digest)
            rebased[str(target)] = digest
        proof['inputs'] = rebased
        write_json(output/relative/'proof.json',proof)
        preview = plan/relative/'preview.urdf'
        if Path(bundle['preview_urdf']) != preview:
            raise ValueError('Unexpected weigh preview path')
        verify_file(preview,bundle['preview_urdf_sha256'])
        if any(m.get('filename','').startswith('file:') for m in ET.parse(preview).findall('.//mesh')):
            raise ValueError('Non-portable weigh preview mesh')
        target_preview = staging.copy(preview,relative/'preview.urdf')
        bundle.update(model_signature=new_base_signature,hardware_binding=new_binding,
            source_sha256=file_hash(output/relative/'proof.json'),preview_urdf=str(target_preview))
        write_json(output/relative/'review.json',bundle)

    files = {str(path.relative_to(output)): file_hash(path)
             for path in sorted(output.rglob("*")) if path.is_file()}
    receipt = dict(schema_version=1, speed_percent=workflow["speed_percent"], checker_sha256=checked["sha256"],
                   weighing_requested=weighing_requested,
                   snapshot_sha256=inputs["observations"]["sha256"], object_pose_sha256=inputs["object_pose"]["sha256"],
                   target_resources=staging.resources, files=files,
                   staged_at=datetime.now(timezone.utc).isoformat())
    write_json(output / "stage-receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "output", "target-root", "target-workspace"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument('--description-share', type=Path,
                        help='Executor-resolved shared uwa_cell_description package directory')
    parser.add_argument('--description-source', type=Path,
                        help='Executor-resolved source directory of symlink-installed description meshes')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error(f"Output directory already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent, prefix=".carton-stage-") as temporary:
        work = Path(temporary) / "plan"
        receipt = stage(args.plan.resolve(strict=True), work, args.target_root, args.target_workspace,
                        args.description_share, args.description_source)
        os.rename(work, output)
    print(json.dumps({"staged": str(output), "checker_sha256": receipt["checker_sha256"],
                      "files": len(receipt["files"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
