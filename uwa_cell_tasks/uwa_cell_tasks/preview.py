"""Local review report with strong contrast and explicit action states."""
import html
import json
from pathlib import Path


def preview(directory):
    directory=Path(directory);parts=[]
    for name in ('state.json','review.json','candidate_failures.json','group.json'):
        path=directory/name
        if path.exists():parts.append('<h2>'+html.escape(name)+'</h2><pre>'+html.escape(json.dumps(json.loads(path.read_text()),indent=2))+'</pre>')
    for image in sorted(directory.glob('**/*inspection.jpg')):
        parts.append('<figure><figcaption>'+html.escape(str(image.relative_to(directory)))+'</figcaption><img src="'+html.escape(str(image.relative_to(directory)),quote=True)+'"></figure>')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><title>UWA task review</title><style>body{background:#101820;color:#fff;font:18px system-ui;max-width:1200px;margin:30px auto}pre{background:#000;padding:20px;white-space:pre-wrap;overflow-wrap:anywhere}img{max-width:100%}h1,h2{color:#ffe76b}figure{border:3px solid #fff;padding:12px}</style><h1>UWA task review — SIMULATION</h1>'+''.join(parts)+'</html>'
    path=directory/'review.html';path.write_text(page);return str(path.resolve())
