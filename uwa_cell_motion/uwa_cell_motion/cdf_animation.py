"""Standalone orbit/slider preview of the conservative frozen-cell model."""
import json
from pathlib import Path
import numpy as np
from .cdf_geometry import FrozenScene


def render(problem,plan,output):
    if not plan.get('success') or plan.get('method')!='cdf' or not plan.get('simulation_only'):raise ValueError('Successful simulation CDF plan required')
    scene=FrozenScene(problem,plan['request']);points=plan['trajectory']['points']
    indices=np.unique(np.linspace(0,len(points)-1,min(300,len(points))).astype(int))
    q=np.asarray([points[i]['positions'] for i in indices]);world=problem.spheres.world(plan['request']['start'])
    fixed=[dict(id=r,centres=centres.tolist(),radii=problem.spheres.radii[r].tolist()) for r,centres in world.items() if r!=scene.arm]
    boxes=[]
    for T,mid,half,label in scene.boxes:
        corners=np.array([[x,y,z] for x in (-1,1) for y in (-1,1) for z in (-1,1)])*half+mid
        boxes.append((corners@T[:3,:3].T+T[:3,3]).tolist())
    data=dict(arm=scene.arm,frames=scene.forward(q)[0].tolist(),radii=scene.radii.tolist(),fixed=fixed,boxes=boxes,
        times=[points[i]['time'] for i in indices],duration=plan['trajectory']['duration_s'])
    template=r'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Single-UR CDF motion preview</title>
<style>body{margin:22px;background:#111a28;color:white;font:18px sans-serif}h1{color:#ffe18a}button,input,select{font:inherit;padding:9px}button{border:3px solid white;background:#144b80;color:white;cursor:pointer}#state{font-weight:bold;border:3px solid #ffe18a;padding:12px;margin:12px 0}canvas{background:#1c293e;width:100%;height:65vh;touch-action:none;border:1px solid white}#slider{width:65%}a{color:#89ddff}</style>
<h1>SIMULATION MODEL — CDF trajectory preview</h1>
<p>One moving UR, three fixed arms. Conservative collision spheres and table boxes. Offline preview: no ROS commands, no Gazebo physics, no real motion.</p>
<div id="state">READY — no motion sent</div><canvas id="view"></canvas>
<p><button id="play">Play preview</button> <button id="reset">Back to start</button> <select id="speed"><option value="1">Preview ×1</option><option value="5" selected>Preview ×5</option><option value="10">Preview ×10</option></select> <span id="clock"></span></p>
<input id="slider" type="range" min="0" value="0" step="1"><p id="legend"></p>
<p>Drag to orbit · mouse wheel to zoom · slider to inspect. Preview speed changes only this animation.</p>
<script>const data=__CDF_DATA__;
const canvas=document.getElementById('view'),ctx=canvas.getContext('2d'),slider=document.getElementById('slider'),state=document.getElementById('state');
const colours=['#64c7ff','#9be078','#ffe08a'];let yaw=-.8,pitch=.6,zoom=1,frame=0,playing=false,t=0,last=performance.now(),drag=null;
slider.max=data.frames.length-1;document.getElementById('legend').textContent='MOVING: '+data.arm+' (white) · FIXED: '+data.fixed.map(x=>x.id).join(', ');
function project(p){let x=p[0],y=p[1],z=p[2]-1.15,h=x*Math.cos(yaw)-y*Math.sin(yaw),d=x*Math.sin(yaw)+y*Math.cos(yaw);return [canvas.width/2+scale*h,canvas.height/2-scale*(z*Math.cos(pitch)-d*Math.sin(pitch)),z*Math.sin(pitch)+d*Math.cos(pitch)];}
let scale=1;function line(a,b,colour){a=project(a);b=project(b);ctx.strokeStyle=colour;ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();}
function draw(){canvas.width=canvas.clientWidth*devicePixelRatio;canvas.height=canvas.clientHeight*devicePixelRatio;scale=Math.min(canvas.width,canvas.height)/3.1*zoom;ctx.clearRect(0,0,canvas.width,canvas.height);ctx.lineWidth=devicePixelRatio;
 for(let i=-1.5;i<=1.5;i+=.25){line([i,-1.5,0],[i,1.5,0],'#4f6279');line([-1.5,i,0],[1.5,i,0],'#4f6279');}
 for(const box of data.boxes)for(let i=0;i<8;i++)for(const mask of [1,2,4])if(!(i&mask))line(box[i],box[i|mask],'#aab6c5');
 let spheres=[];function add(centres,radii,colour){centres.forEach((c,i)=>{let p=project(c);spheres.push({p,r:radii[i]*scale,colour});});}
 data.fixed.forEach((arm,i)=>add(arm.centres,arm.radii,colours[i]));add(data.frames[frame],data.radii,'#ffffff');spheres.sort((a,b)=>a.p[2]-b.p[2]);
 for(const s of spheres){ctx.beginPath();ctx.arc(s.p[0],s.p[1],Math.max(1,s.r),0,2*Math.PI);ctx.fillStyle=s.colour;ctx.globalAlpha=.8;ctx.fill();ctx.globalAlpha=1;ctx.strokeStyle='#172233';ctx.stroke();}
 document.getElementById('clock').textContent=data.times[frame].toFixed(2)+' / '+data.duration.toFixed(2)+' planned seconds';slider.value=frame;
}
function pause(label){playing=false;document.getElementById('play').textContent='Play preview';state.textContent=label+' — no motion sent';}
document.getElementById('play').onclick=()=>{if(playing)pause('PREVIEW PAUSED');else{if(t>=data.duration){t=0;frame=0;}playing=true;last=performance.now();state.textContent='PREVIEW PLAYING — no motion sent';document.getElementById('play').textContent='Pause preview';}};
document.getElementById('reset').onclick=()=>{pause('READY');frame=0;t=0;draw();};slider.oninput=()=>{pause('PREVIEW PAUSED');frame=Number(slider.value);t=data.times[frame];draw();};
canvas.onpointerdown=e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);};canvas.onpointerup=()=>drag=null;canvas.onpointermove=e=>{if(drag){yaw+=(e.clientX-drag[0])*.008;pitch=Math.max(-1.4,Math.min(1.4,pitch+(e.clientY-drag[1])*.008));drag=[e.clientX,e.clientY];draw();}};
canvas.onwheel=e=>{e.preventDefault();zoom=Math.max(.3,Math.min(4,zoom*Math.exp(-e.deltaY*.001)));draw();};window.onresize=draw;
function loop(now){if(playing){t=Math.min(data.duration,t+(now-last)/1000*Number(document.getElementById('speed').value));while(frame+1<data.times.length&&data.times[frame+1]<=t)frame++;draw();if(t>=data.duration)pause('PREVIEW COMPLETE');}last=now;requestAnimationFrame(loop);}draw();requestAnimationFrame(loop);
</script></html>'''
    Path(output).write_text(template.replace('__CDF_DATA__',json.dumps(data,separators=(',',':')).replace('</',r'<\/')))
