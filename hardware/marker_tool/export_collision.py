#!/usr/bin/env python3
"""Export the accepted STEP solids in adapter-local metres for offline pen handling."""
import hashlib
import json
from pathlib import Path
import tempfile

from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.StlAPI import StlAPI_Writer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
import trimesh

p=Path(__file__).resolve().parent
r=STEPControl_Reader()
assert r.ReadFile(str(p/'marker-werkzeug.step'))==IFSelect_RetDone and r.TransferRoots()
bodies=[];e=TopExp_Explorer(r.OneShape(),TopAbs_SOLID)
with tempfile.TemporaryDirectory() as tmp:
    while e.More():
        s=e.Current();b=Bnd_Box();BRepBndLib.AddOptimal_s(s,b)
        BRepMesh_IncrementalMesh(s,.12,False,.22,False)
        path=Path(tmp)/'part.stl';assert StlAPI_Writer().Write(s,str(path))
        bodies.append((b.CornerMin().Z(),b.CornerMin().Y(),trimesh.load_mesh(path)))
        e.Next()
assert len(bodies)==3
bodies.sort(key=lambda v:(v[0],v[1]))
out=p.parents[1]/'uwa_cell_description/assets/pen_grasp_v1';out.mkdir(exist_ok=True)
for n,(_,_,mesh) in enumerate(bodies):
    if n:mesh.apply_translation([0,0,-89.5])
    mesh.apply_scale(.001)
    assert mesh.is_watertight
    mesh.export(out/('dock.stl' if n==0 else f'adapter-{n}.stl'))
(out/'manifest.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256((p/'marker-werkzeug.step').read_bytes()).hexdigest(),
    units='m',adapter_origin='STEP world minus89.5mm Z; top49mm; nominal tip -79mm',
    files={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.glob('*.stl'))}),indent=2)+'\n')
