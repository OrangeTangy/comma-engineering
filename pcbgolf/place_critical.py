#!/usr/bin/env python3
"""Experimental underside circuit grouping; run with KiCad bundled Python.
Distances and AABBs are heuristics. Native DRC, routing and thermal review required.
Copies an integrated project; never edits the source. No pin assignments change.
"""
import pcbnew as p, argparse, shutil, json, math
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('destination',type=Path);a=ap.parse_args()
assert a.source.resolve()!=a.destination.resolve()
shutil.copytree(a.source,a.destination,dirs_exist_ok=True)
b=p.LoadBoard(str(a.destination/'pcbgolf.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()}
def xy(v):return p.ToMM(v.x),p.ToMM(v.y)
def vec(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def box(f):
 pts=[]
 for pad in f.Pads():
  z=pad.GetBoundingBox();pts.extend([xy(z.GetOrigin()),xy(z.GetEnd())])
 for g in f.GraphicalItems():
  if g.GetLayer() in (p.F_Fab,p.B_Fab,p.F_CrtYd,p.B_CrtYd):
   z=g.GetBoundingBox();pts.extend([xy(z.GetOrigin()),xy(z.GetEnd())])
 return min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)
def overlap(z,q,gap=.25):return z[0]<q[2]+gap and q[0]<z[2]+gap and z[1]<q[3]+gap and q[1]<z[3]+gap
power1=['U1','C4','C2','L1','C1','R3','R4','R5','R6','R1','C6','C7','C8']
power2=['U2','C9','C5','L2','C3','R9','R10','R7','R8','C10','C11','C12','C13']
clock1=['Y1','C14','C17'];clock2=['Y2','C28','C32','R26']
bypass=['L3','L4']+['C'+str(i) for i in range(15,28) if i!=17]
moving=set(power1+power2+clock1+clock2+bypass)
before={(r,pad.GetNumber()):(pad.GetNetname(),xy(pad.GetPosition())) for r,f in fs.items() for pad in f.Pads()}
obstacles=[]
for r,f in fs.items():
 if r in moving:continue
 if f.GetLayer()==p.B_Cu:obstacles.append(box(f))
 for pad in f.Pads():
  if pad.GetAttribute() in (p.PAD_ATTRIB_PTH,p.PAD_ATTRIB_NPTH):
   z=pad.GetBoundingBox();obstacles.append((*xy(z.GetOrigin()),*xy(z.GetEnd())))
report=[]
def place(r,targets,anchor,limit=10):
 f=fs[r]
 if f.GetLayer()!=p.B_Cu:f.Flip(f.GetPosition(),False)
 # Only listed circuit members attract a component. Avoid attraction to global rails.
 tp={}
 for tr in targets:
  for pad in fs[tr].Pads():tp.setdefault(pad.GetNetname(),[]).append(xy(pad.GetPosition()))
 best=None
 for rot in (0,90,180,270):
  f.SetOrientationDegrees(rot);f.SetPosition(vec(0,0));z=box(f)
  pads=[(pad.GetNetname(),xy(pad.GetPosition())) for pad in f.Pads()]
  for ix in range(-int(limit*4),int(limit*4)+1):
   x=anchor[0]+ix*.25
   for iy in range(-int(limit*4),int(limit*4)+1):
    y=anchor[1]+iy*.25;q=(z[0]+x,z[1]+y,z[2]+x,z[3]+y)
    if q[0]<.4 or q[1]<.4 or q[2]>69.6 or q[3]>59.6:continue
    if any(overlap(q,o) for o in obstacles):continue
    score=.04*((x-anchor[0])**2+(y-anchor[1])**2)
    for net,(px,py) in pads:
     if net in tp and net and not net.startswith('unconnected-'):
      # Squared distances penalize a single long critical connection.
      score+=min((x+px-tx)**2+(y+py-ty)**2 for tx,ty in tp[net])
    candidate=(score,rot,x,y,q)
    if best is None or candidate[:4]<best[:4]:best=candidate
 assert best is not None,r
 score,rot,x,y,q=best;f.SetOrientationDegrees(rot);f.SetPosition(vec(x,y));obstacles.append(q)
 report.append(dict(ref=r,x=x,y=y,rotation=rot,layer='B.Cu',heuristic_cost=score,targets=targets))
for group,anchor in [(power2,(14,49)),(power1,(31,49))]:
 place(group[0],[],anchor,0)
 for r in group[1:]:place(r,[group[0]]+group[1:group.index(r)],anchor,10)
for group,ic,pins in [(clock1,'U3',('25','26')),(clock2,'U4',('60','61'))]:
 pp=[xy(t.GetPosition()) for t in fs[ic].Pads() if t.GetNumber() in pins];anchor=tuple(sum(x[i] for x in pp)/len(pp) for i in (0,1))
 for r in group:place(r,[ic]+group[:group.index(r)],anchor,7)
for r in bypass:place(r,['U3']+([ 'L3'] if r=='C22' else []),xy(fs['U3'].GetPosition()),12)
after={(r,pad.GetNumber()):pad.GetNetname() for r,f in fs.items() for pad in f.Pads()}
assert all(after[k]==v[0] for k,v in before.items()),'Net assignment changed'
p.SaveBoard(str(a.destination/'pcbgolf.kicad_pcb'),b)
metrics=[]
for ra,pa,rb,pb in [('U1','6','C4','1'),('U1','2','L1','1'),('U1','3','C2','1'),('U2','6','C9','1'),('U2','2','L2','1'),('U2','3','C5','1'),('U3','25','Y1','1'),('U3','26','Y1','3'),('U4','61','Y2','1'),('U4','60','Y2','3')]:
 def new(r,n):return xy(next(t for t in fs[r].Pads() if t.GetNumber()==n).GetPosition())
 metrics.append(dict(connection=f'{ra}.{pa}--{rb}.{pb}',before_mm=math.dist(before[ra,pa][1],before[rb,pb][1]),after_mm=math.dist(new(ra,pa),new(rb,pb))))
result=dict(status='UNROUTED_EXPERIMENT',method='circuit-specific pad distance and conservative 2D body exclusion',net_assignments_preserved=True,moved=report,critical_distances=metrics,limitations=['No routing or loop inductance model','Opposite-side clock vias required','Power return and thermal copper not designed','MCU bypass assignments need datasheet review','Assembly clearance requires STEP verification'])
(a.destination.parent/'critical-placement.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(metrics,indent=2))
