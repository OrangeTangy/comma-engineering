#!/usr/bin/env python3
"""Rebuild the golf-v2 PCB: new connector footprints, two copper layers, a notched outline
and a two-sided placement. Run with KiCad's bundled Python:

  place_golf_v2.py golf-v2 golf-v2-bodies.json --width 50 --height 46

Placement is simulated annealing over half-perimeter wirelength with per-side body
rectangles (from 3D models, see golf-v2-bodies.json). Connectors are fixed on the edges.
Parts up to 1.8 mm tall may go underneath: the mid-mount jack already extends 2.05 mm
below the board, so they add no assembly height. Net assignments are checked unchanged.
"""
import pcbnew as p,argparse,json,math,random
from pathlib import Path

ap=argparse.ArgumentParser()
ap.add_argument('project',type=Path);ap.add_argument('bodies',type=Path)
ap.add_argument('--width',type=float,default=50);ap.add_argument('--height',type=float,default=46)
ap.add_argument('--seed',type=int,default=1);ap.add_argument('--moves',type=int,default=400000)
ap.add_argument('--report',type=Path)
ap.add_argument('--bottom-cost',type=float,default=2.0,help='penalty per part underneath (routing space, vias)')
ap.add_argument('--route-margin',type=float,default=0.0,help='extra clearance per sqrt(pin count), mm: room for escape routing')
a=ap.parse_args();random.seed(a.seed);W,H=a.width,a.height
bodies=json.loads(a.bodies.read_text())
b=p.LoadBoard(str(a.project/'pcbgolf.kicad_pcb'))
def mm(v):return p.ToMM(v.x),p.ToMM(v.y)
def vec(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))

# Two copper layers, no copper or outline from earlier trials.
removed=[]  # keep Python references: SWIG would otherwise free items the board still indexes
removed+=list(b.Zones())+list(b.GetTracks())+[d for d in b.GetDrawings() if d.GetLayer()==p.Edge_Cuts]
removed+=[f for f in b.GetFootprints() if f.GetReference().startswith('BH')]  # optional DNP M2 holes
for item in removed:b.Remove(item)
b.SetCopperLayerCount(2)

# Swap connector footprints, keeping the schematic link and each pad's net by number.
before={(f.GetReference(),pad.GetNumber()):pad.GetNetname() for f in b.GetFootprints() for pad in f.Pads() if pad.GetNumber()}
SWAP={'J1':'PJ-107AH-MSMT',**{f'J{i}':'DX07S024XJ1R1100_OBDC' for i in (5,6,7,8)}}
lib=str(a.project/'pcbgolf.pretty')
for ref,name in SWAP.items():
    old=next(f for f in b.GetFootprints() if f.GetReference()==ref)
    nets={pad.GetNumber():pad.GetNet() for pad in old.Pads() if pad.GetNumber()}
    new=p.FootprintLoad(lib,name);new.SetFPID(p.LIB_ID('pcbgolf',name))
    new.SetReference(ref);new.SetValue(old.GetValue())
    for fld in old.GetFields():
        if fld.GetName() not in ('Reference','Value','Footprint','Datasheet','Description'):
            new.SetField(fld.GetName(),fld.GetText())
    new.SetField('MPN',{'J1':'PJ-107AH-MSMT-TR'}.get(ref,'DX07S024XJ1R1100'))
    for fld in new.GetFields():
        if fld.GetName() not in ('Reference',):fld.SetVisible(False)
    new.SetPath(old.GetPath());new.SetSheetname(old.GetSheetname());new.SetSheetfile(old.GetSheetfile())
    b.Remove(old);removed.append(old);b.Add(new)
    for pad in new.Pads():
        if pad.GetNumber() in nets:pad.SetNet(nets[pad.GetNumber()])
fs={f.GetReference():f for f in b.GetFootprints()}

# Local geometry of every footprint (front side, orientation 0, origin at 0,0).
GAP=0.25  # margin around parts without a courtyard (KiCad's standard courtyard clearance)
TOP_ONLY=('CHIPLED','CREE-RGB-CLMVC','CHOKE-3.2X2.5','DO-214AA(SMB)','EVQ-Q2','LQFP-144_20x20mm_P0.5mm')
parts={}
fixed_refs={'J1','J2','J3','J5','J6','J7','J8'}
for ref,f in fs.items():
    if f.IsFlipped():f.Flip(f.GetPosition(),p.FLIP_DIRECTION_LEFT_RIGHT)
    f.SetOrientationDegrees(0);f.SetPosition(vec(0,0))
    name=str(f.GetFPID().GetLibItemName());body=bodies[name]
    pads=[];x0,y0,x1,y1=body['rect']
    tht=False
    crt=f.GetCourtyard(p.F_CrtYd)

    if crt.OutlineCount():
        # Use the library courtyard (already includes clearance) so native DRC finds no overlaps.
        bb=crt.BBox();(cx0,cy0),(cx1,cy1)=mm(bb.GetOrigin()),mm(bb.GetEnd())
        x0,y0,x1,y1=min(x0,cx0+GAP-0.02),min(y0,cy0+GAP-0.02),max(x1,cx1-GAP+0.02),max(y1,cy1-GAP+0.02)
    for pad in f.Pads():
        px,py=mm(pad.GetPosition());bb=pad.GetBoundingBox();(ax,ay),(bx,by)=mm(bb.GetOrigin()),mm(bb.GetEnd())
        x0,y0,x1,y1=min(x0,ax),min(y0,ay),max(x1,bx),max(y1,by)
        tht|=pad.GetAttribute() in (p.PAD_ATTRIB_PTH,p.PAD_ATTRIB_NPTH)
        if pad.GetNetname() and pad.GetNetname()!='GND' and not pad.GetNetname().startswith('unconnected-'):
            pads.append((pad.GetNetname(),px,py))
    m=GAP+a.route_margin*math.sqrt(len(list(f.Pads())))*(ref not in fixed_refs)
    parts[ref]=dict(name=name,pads=pads,rect=(x0-m,y0-m,x1+m,y1+m),margin=m-GAP,both=tht,
                    flip_ok=not tht and body['height']<=1.8 and name not in TOP_ONLY)

def place_pts(ref,x,y,rot,side,pts):
    """KiCad convention (measured): the bottom side mirrors local y, then rotates CCW on screen (y down)."""
    c,s=round(math.cos(math.radians(rot))),round(math.sin(math.radians(rot)))
    out=[]
    for px,py in pts:
        if side:py=-py
        out.append((x+px*c+py*s,y-px*s+py*c))
    return out
def rect_of(ref,st):
    x0,y0,x1,y1=parts[ref]['rect'];q=place_pts(ref,*st,[(x0,y0),(x1,y1)])
    return min(q[0][0],q[1][0]),min(q[0][1],q[1][1]),max(q[0][0],q[1][0]),max(q[0][1],q[1][1])

# Fixed connectors: four OBD-C ports facing the top edge at the 12.85 mm minimum pitch,
# jack, host USB-C and microSD on the bottom edge. Mating faces are flush with the edge.
JX=9.0
fixed={f'J{5+i}':(W/2+(i-1.5)*12.85,8.85,180,0) for i in range(4)}
fixed.update({'J1':(JX,H-12.6,0,0),'J3':(JX+12.4,H-8.85,0,0),'J2':(W-14.8,H-11.99,180,0)})
state={}
for ref in parts:
    state[ref]=fixed.get(ref) or (random.uniform(3,W-3),random.uniform(12,H-14),random.choice((0,90,180,270)),0)
# The 144-pin MCU's position is pinned between the port row and the bottom connectors, clear of
# the jack (courtyard x <= JX+6.7) and the microSD socket; only its rotation is optimised.
ux0,uy0,ux1,uy1=rect_of('U3',(0,0,0,0))
port_bottom=max(rect_of(r,fixed[r])[3] for r in ('J5','J6','J7','J8'))
state['U3']=(rect_of('J1',fixed['J1'])[2]-ux0+0.02,port_bottom-uy0+0.02,0,0);pinned={'U3'}
movable=[r for r in parts if r not in fixed]

# Nets: GND is a pour; rails are weighted lightly so decoupling is handled separately.
RAILS={'+3V3','+5V','+12V','VDDLDO','VBUS','VDDA','Net-(J1-PWR)'}
netpins={}
for ref,pt in parts.items():
    for i,(n,_,_) in enumerate(pt['pads']):netpins.setdefault(n,[]).append((ref,i))
weight={n:(0.15 if n in RAILS else 1.0) for n in netpins}
padpos={}
def update_pads(ref):
    st=state[ref];padpos[ref]=place_pts(ref,*st,[(x,y) for _,x,y in parts[ref]['pads']])
for r in parts:update_pads(r)
def hpwl(n):
    xs=[padpos[r][i][0] for r,i in netpins[n]];ys=[padpos[r][i][1] for r,i in netpins[n]]
    return weight[n]*(max(xs)-min(xs)+max(ys)-min(ys))
# Decoupling: two-terminal parts between a rail and GND are pulled to the nearest IC rail pin.
ics=[r for r,pt in parts.items() if len(pt['pads'])>=6 and not r.startswith('J')]
decap={}
for r,f in fs.items():
    nets={pad.GetNetname() for pad in f.Pads()}
    if len(list(f.Pads()))==2 and 'GND' in nets and len(nets&RAILS)==1:decap[r]=(nets&RAILS).pop()
rail_pins={}
for ic in ics:
    for k,(n,_,_) in enumerate(parts[ic]['pads']):
        if n in RAILS:rail_pins.setdefault(n,[]).append((ic,k))
def decap_cost(r):
    rail=decap[r];i=next(k for k,(n,_,_) in enumerate(parts[r]['pads']) if n==rail);x,y=padpos[r][i]
    return min((abs(x-padpos[ic][k][0])+abs(y-padpos[ic][k][1]) for ic,k in rail_pins.get(rail,())),default=0)
def overlap(r1,r2):
    w=min(r1[2],r2[2])-max(r1[0],r2[0]);h=min(r1[3],r2[3])-max(r1[1],r2[1])
    return w*h if w>0 and h>0 else 0.0
def sides(ref):return (0,1) if parts[ref]['both'] else (state[ref][3],)
def out_of_board(q,ref=None):
    """Distance outside the board, ignoring the routing margin (it may extend past the edge)."""
    k=parts[ref]['margin'] if ref else 0;q=(q[0]+k,q[1]+k,q[2]-k,q[3]-k)
    return max(0,0.3-q[0])+max(0,q[2]-(W-0.3))+max(0,0.3-q[1])+max(0,q[3]-(H-0.3))
CELL=3.0
grid={}
def cells(ref):
    q=rects[ref]
    return [(sd,i,j) for sd in sides(ref) for i in range(int(q[0]//CELL),int(q[2]//CELL)+1) for j in range(int(q[1]//CELL),int(q[3]//CELL)+1)]
registered={}
def set_rect(ref,q):
    for c in registered.get(ref,()):grid[c].discard(ref)
    rects[ref]=q;registered[ref]=cells(ref)
    for c in registered[ref]:grid.setdefault(c,set()).add(ref)
rects={}
for r in parts:set_rect(r,rect_of(r,state[r]))
def part_overlap(ref):
    q=rects[ref];near=set()
    for c in registered[ref]:near|=grid.get(c,set())
    near.discard(ref)
    return sum(overlap(q,rects[o]) for o in near)

lam=0.5
def local_cost(ref,nets):
    c=sum(hpwl(n) for n in nets)+lam*part_overlap(ref)+(0 if ref in fixed else 20*out_of_board(rects[ref],ref))
    if ref in decap:c+=decap_cost(ref)
    c+=a.bottom_cost*state[ref][3]
    return c
ref_nets={r:{n for n,_,_ in parts[r]['pads']} for r in parts}

T0,T1=8.0,0.02
for k in range(a.moves):
    frac=k/a.moves;T=T0*(T1/T0)**frac;lam=0.5+400*frac**2
    r=random.choice(movable);old=state[r];nets=ref_nets[r]
    mv=random.random();x,y,rot,side=old;other=None
    if r in pinned and (mv<0.6 or mv>=0.85):continue
    if mv<0.6:
        s=max(0.2,12*(1-frac)**2);x+=random.gauss(0,s);y+=random.gauss(0,s)
    elif mv<0.75:rot=(rot+random.choice((90,180,270)))%360
    elif mv<0.85:
        if not parts[r]['flip_ok']:continue
        side=1-side
    else:
        other=random.choice(movable)
        if other==r or other in pinned:continue
    if other:
        nets=nets|ref_nets[other];oo=state[other]
        c0=local_cost(r,nets)+lam*part_overlap(other)
        state[r]=(oo[0],oo[1],old[2],old[3]);state[other]=(old[0],old[1],oo[2],oo[3])
        if (state[r][3] and not parts[r]['flip_ok']) or (state[other][3] and not parts[other]['flip_ok']):
            state[r],state[other]=old,oo;continue
        for q in (r,other):update_pads(q);set_rect(q,rect_of(q,state[q]))
        c1=local_cost(r,nets)+lam*part_overlap(other)
        if c1>c0 and random.random()>=math.exp((c0-c1)/T):
            state[r],state[other]=old,oo
            for q in (r,other):update_pads(q);set_rect(q,rect_of(q,state[q]))
        continue
    c0=local_cost(r,nets)
    state[r]=(x,y,rot,side);update_pads(r);set_rect(r,rect_of(r,state[r]))
    c1=local_cost(r,nets)
    if c1>c0 and random.random()>=math.exp((c0-c1)/T):
        state[r]=old;update_pads(r);set_rect(r,rect_of(r,old))

# Legalise: slide any part that still overlaps to the cheapest free spot nearby.
def legal(ref):return part_overlap(ref)==0 and out_of_board(rects[ref],ref)==0
def area(r):q=parts[r]['rect'];return (q[2]-q[0])*(q[3]-q[1])
def overlapping(r):
    near=set()
    for c in registered[r]:near|=grid.get(c,set())
    return [o for o in near if o!=r and overlap(rects[r],rects[o])>0]
def relocate(r):
        x0,y0,rot0,side0=state[r];best=None
        for rad in [i*0.25 for i in range(1,80)]:
            for ang in range(0,360,15):
                for rot in (rot0,(rot0+90)%360):
                    for side in ((side0,1-side0) if parts[r]['flip_ok'] else (side0,)):
                        state[r]=(x0+rad*math.cos(math.radians(ang)),y0+rad*math.sin(math.radians(ang)),rot,side)
                        update_pads(r);set_rect(r,rect_of(r,state[r]))
                        if legal(r):
                            c=local_cost(r,ref_nets[r])
                            if best is None or c<best[0]:best=(c,state[r])
            if best:break
        state[r]=best[1] if best else (x0,y0,rot0,side0);update_pads(r);set_rect(r,rect_of(r,state[r]))
for sweep in range(6):
    bad=sorted((r for r in movable if not legal(r)),key=area,reverse=True)
    if not bad:break
    for r in bad:
        if legal(r):continue
        # Large parts stay; the smaller parts they overlap move out of the way.
        for o in overlapping(r):
            if o in movable and o not in pinned and area(o)<area(r):relocate(o)
        if not legal(r) and r not in pinned:relocate(r)
illegal={r:overlapping(r) or 'outside' for r in movable if not legal(r)}

# Apply to the board and check the placement model against KiCad's own pad positions.
for ref,(x,y,rot,side) in state.items():
    f=fs[ref]
    if side:f.Flip(f.GetPosition(),p.FLIP_DIRECTION_LEFT_RIGHT)
    f.SetOrientationDegrees(rot);f.SetPosition(vec(x,y))
    got=[mm(pad.GetPosition()) for pad in f.Pads() if pad.GetNetname() and pad.GetNetname()!='GND' and not pad.GetNetname().startswith('unconnected-')]
    assert all(math.dist(g,e)<0.01 for g,e in zip(got,padpos[ref])),(ref,got[:2],padpos[ref][:2])

# Outline with the jack notch (datasheet: x -6.0..+4.3 from the centre pin, from 1.9 mm to the edge).
nx0,nx1,ny=JX-6.0,JX+4.3,H-12.6+1.9
pts=[(0,0),(W,0),(W,H),(nx1,H),(nx1,ny),(nx0,ny),(nx0,H),(0,H)]
for (x0,y0),(x1,y1) in zip(pts,pts[1:]+pts[:1]):
    s=p.PCB_SHAPE(b);s.SetShape(p.SHAPE_T_SEGMENT);s.SetLayer(p.Edge_Cuts);s.SetWidth(p.FromMM(0.05))
    s.SetStart(vec(x0,y0));s.SetEnd(vec(x1,y1));b.Add(s)

after={(f.GetReference(),pad.GetNumber()):pad.GetNetname() for f in b.GetFootprints() for pad in f.Pads() if pad.GetNumber()}
changed=[k for k,v in before.items() if k in after and after[k]!=v]
assert not changed,changed[:10]
p.SaveBoard(str(a.project/'pcbgolf.kicad_pcb'),b)
total=sum(hpwl(n) for n in netpins)
report=dict(width_mm=W,height_mm=H,seed=a.seed,moves=a.moves,weighted_hpwl=round(total,1),
    bottom_side=sorted(r for r in parts if state[r][3]),illegal=illegal)
if a.report:a.report.write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='bottom_side'}),len(report['bottom_side']),'parts underneath')
