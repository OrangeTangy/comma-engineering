#!/usr/bin/env python3
"""Experimental all-top placement, using conservative 2D geometry proxies.
Does not route, validate 3D geometry, establish electrical correctness or score.
Preserves every footprint, pad net and UUID. No rotation or footprint substitution.
"""
import argparse,json,math,random,re,shutil,csv,uuid
from pathlib import Path
from analyze import audit

def main():
 ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args()
 original=audit(a.source);fs=original['footprints'];byref={f['ref']:f for f in fs};rng=random.Random(20261015)
 W,H=70.,60.;gap=.25
 boxes={f['ref']:f['geometry_bbox'] for f in fs}
 positions={};fixed={'J5':(10.,5.),'J6':(22.85,5.),'J7':(35.70,5.),'J8':(48.55,5.),'J1':(5.25,50.),'J2':(68.,22.),'J3':(60.,50.9)}
 # USB plug envelope of at least 12.85 by 7.0 mm for vertical receptacles.
 for r in ['J5','J6','J7','J8']: boxes[r]=[-6.425,-3.5,6.425,3.5]
 # Connector slots share their envelope boundary; no extra gap between envelopes.
 def rect(r,p):
  x,y=p;b=boxes[r];return (x+b[0],y+b[1],x+b[2],y+b[3])
 def valid(r,p):
  b=rect(r,p)
  if b[0]<0 or b[1]<0 or b[2]>W or b[3]>H:return False
  for s,q in positions.items():
   if s==r:continue
   c=rect(s,q);g=0 if r in fixed and s in fixed else gap
   if b[0]<c[2]+g-1e-8 and b[2]>c[0]-g+1e-8 and b[1]<c[3]+g-1e-8 and b[3]>c[1]-g+1e-8:return False
  return True
 for r,p in fixed.items():
  assert valid(r,p),(r,'fixed envelope conflict');positions[r]=p
 nets=original['netpads'];members={r:[] for r in byref}
 # Global rails are excluded from attraction; their planes/current paths need explicit routing.
 globalnets={n for n,ps in nets.items() if len(ps)>24}
 local={}
 for n,ps in nets.items():
  if n in globalnets or len(ps)<2:continue
  local[n]=[(r,x-byref[r]['x'],y-byref[r]['y']) for r,p,x,y in ps]
  for r in {p[0] for p in ps}:members[r].append(n)
 def cost(r,p):
  total=0
  for n in members[r]:
   pts=[]
   for s,dx,dy in local[n]:
    q=p if s==r else positions.get(s)
    if q:pts.append((q[0]+dx,q[1]+dy))
   if len(pts)>1:total+=max(x for x,y in pts)-min(x for x,y in pts)+max(y for x,y in pts)-min(y for x,y in pts)
  return total
 todo=sorted((r for r in byref if r not in fixed),key=lambda r:-(boxes[r][2]-boxes[r][0])*(boxes[r][3]-boxes[r][1]))
 for r in todo:
  b=boxes[r];choices=[]
  # Half-mm grid controls repeatability; min corner offset preserves package envelope.
  for ix in range(int((W-b[2]+b[0])*2)+1):
   for iy in range(int((H-b[3]+b[1])*2)+1):
    p=(round(-b[0]+ix*.5,5),round(-b[1]+iy*.5,5))
    if valid(r,p):choices.append((cost(r,p)+.0001*(p[0]+p[1]),p))
  if not choices:raise RuntimeError(f'Cannot place {r}; expand envelope, do not silently overlap')
  positions[r]=min(choices)[1]
 initial=sum(cost(r,p) for r,p in positions.items())
 # Local search minimizes signal span while enforcing zero proxy overlaps.
 accepted=0
 for step in range(30000):
  r=rng.choice(todo);p=positions[r];radius=4 if step<15000 else 1
  q=(round(p[0]+rng.uniform(-radius,radius),3),round(p[1]+rng.uniform(-radius,radius),3))
  if valid(r,q) and cost(r,q)<cost(r,p):positions[r]=q;accepted+=1
 # Export by modifying only the global footprint origin in each top-level block.
 s=a.source.read_text();matches=list(re.finditer(r'^\t\(footprint\b',s,re.M));changes=[]
 for i,m in enumerate(matches):
  end=matches[i+1].start() if i+1<len(matches) else len(s)
  chunk=s[m.start():end];ref=re.search(r'\(property "Reference" "([^"]+)"',chunk).group(1)
  match=re.search(r'^\t\t\(at ([^\n]+)\)',chunk,re.M)
  tail=match.group(1).split()[2:];p=positions[ref]
  replacement=f'(at {p[0]:.5f} {p[1]:.5f}'+(' '+' '.join(tail) if tail else '')+')'
  lo=m.start()+match.start()+2;hi=m.start()+match.end();changes.append((lo,hi,replacement))
 for lo,hi,replacement in reversed(changes):s=s[:lo]+replacement+s[hi:]
 edges=''
 for p,q in [((0,0),(W,0)),((W,0),(W,H)),((W,H),(0,H)),((0,H),(0,0))]:
  edges+=f'\n\t(gr_line (start {p[0]} {p[1]}) (end {q[0]} {q[1]}) (stroke (width 0.05) (type default)) (layer "Edge.Cuts") (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,str((p,q)))}"))'
 s=s.rstrip();s=s[:-1]+edges+'\n)\n'
 a.output.mkdir(parents=True,exist_ok=True)
 for p in a.source.parent.iterdir():
  if p.name.startswith('.') or p.name in ['assets','README.md']:continue
  if p.is_dir():shutil.copytree(p,a.output/p.name,dirs_exist_ok=True)
  else:shutil.copy2(p,a.output/p.name)
 target=a.output/a.source.name;target.write_text(s)
 updated=audit(target)
 def signature(report):return sorted((n,r,p) for n,ps in report['netpads'].items() for r,p,x,y in ps)
 assert signature(original)==signature(updated),'Pad/net assignment changed'
 assert len(updated['footprints'])==len(fs)
 assert all(valid(r,p) for r,p in positions.items()),'Proxy overlap'
 result=dict(status='UNROUTED_PLACEMENT_STUDY',board_outline_mm=[W,H],proxy_clearance_mm=gap,seed=20261015,accepted_moves=accepted,initial_local_objective=initial,final_local_objective=sum(cost(r,p) for r,p in positions.items()),baseline_all_net_hpwl_mm=original['total_hpwl_mm'],candidate_all_net_hpwl_mm=updated['total_hpwl_mm'],pad_net_identity_preserved=True,validated_score=None,native_drc='NOT_RUN',assembly_step='NOT_VALIDATED',missing_courtyard_count=len(original['unverified_courtyards']))
 (a.output.parent/'placement-results.json').write_text(json.dumps(result,indent=2)+'\n')
 with (a.output.parent/'placement.csv').open('w') as out:
  wr=csv.writer(out);wr.writerow(['reference','x_mm','y_mm','rotation_deg']);wr.writerows((r,*p,byref[r]['rotation']) for r,p in sorted(positions.items()))
 # Geometry proxy drawing explicitly avoids presenting rectangles as verified packages.
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-3 -10 {W+6} {H+18}"><rect x="-3" y="-10" width="{W+6}" height="{H+18}" fill="#f3f5f7"/><text x="0" y="-6" font-family="sans-serif" font-size="2">UNROUTED 70 × 60 mm — geometry proxies, not DRC</text><rect width="{W}" height="{H}" fill="#15382e"/>']
 for r,p in positions.items():
  b=rect(r,p);color='#f5b642' if r.startswith('J') else '#65b9d5' if r.startswith('U') else '#b7cfc5'
  svg.append(f'<rect x="{b[0]}" y="{b[1]}" width="{b[2]-b[0]}" height="{b[3]-b[1]}" fill="{color}" stroke="#20352f" stroke-width=".1"/><text x="{p[0]}" y="{p[1]}" text-anchor="middle" font-family="sans-serif" font-size="1">{r}</text>')
 svg.append('</svg>');(a.output.parent/'placement.svg').write_text(''.join(svg))
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
