"""Content binding of the Return to Home cell model across ROSmini and N100."""

import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from uwa_cell_control.parallel_scan import collision_signature


def model_identity(problem):
    tree = ET.fromstring(problem.description)
    meshes = {}
    for mesh in tree.findall("./link/collision/geometry/mesh"):
        uri = mesh.get("filename")
        if uri not in meshes:
            url = urlsplit(uri)
            if url.scheme != "file" or url.netloc:
                raise ValueError("Model identity requires a local resolved mesh.")
            meshes[uri] = hashlib.sha256(Path(unquote(url.path)).read_bytes()).hexdigest()
        mesh.set("filename", "sha256:" + meshes[uri])
    collision = collision_signature(ET.tostring(tree, encoding="unicode"))
    srdf = ET.parse(problem.directory / "moveit/robot.srdf")
    exemptions = sorted(tuple(sorted((pair.get("link1"), pair.get("link2"))))
                        for pair in srdf.findall("disable_collisions"))
    return hashlib.sha256(json.dumps(dict(collision=collision, exemptions=exemptions,
        config=problem.cfg), sort_keys=True, allow_nan=False).encode()).hexdigest()
