#!/usr/bin/env python3
"""KiCad source audit. stdlib only. Intentionally does NOT certify DRC/score."""
import argparse,collections,json,math,re,hashlib
from pathlib import Path

def parse(s):
    toks=re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+',s)
    stack=[];root=None
    for t in toks:
        if t=='(':
            v=[]
            if stack: stack[-1].append(v)
            else: root=v
            stack.append(v)
        elif t==')': stack.pop()
        else: stack[-1].append(json.loads(t) if t.startswith('"') else t)
    return root

def items(n,k): return [x for x in n if isinstance(x,list) and x and x[0]==k]
def one(n,k,default=None):
    v=items(n,k)
    return v[0] if v else default

def points(n):
    out=[]
    for k in ('start','end','center','mid','xy'):
        for p in items(n,k): out.append(tuple(map(float,p[1:3])))
    for p in items(n,'pts'): out+=points(p)
    return out

def audit(path):
    raw=path.read_text(); b=parse(raw); fps=[]; netpads=collections.defaultdict(list)
    for f in items(b,'footprint'):
        prop={p[1]:p[2] for p in items(f,'property')}; ref=prop['Reference']
        at=list(map(float,one(f,'at')[1:]));x,y=at[:2];ang=math.radians(at[2] if len(at)>2 else 0)
        def transform(px,py): return (x+px*math.cos(ang)+py*math.sin(ang),y-px*math.sin(ang)+py*math.cos(ang))
        pads=items(f,'pad'); local=[]
        for p in pads:
            a=one(p,'at',['at','0','0']); px,py=map(float,a[1:3]);sz=one(p,'size',['size','0','0']);w,h=map(float,sz[1:3])
            # Conservative circle enclosing the rotated pad (not exact clearance geometry).
            r=math.hypot(w,h)/2;local += [(px-r,py-r),(px+r,py+r)]
            net=one(p,'net',['net',''])[1:];netname=net[-1] if net else ''
            if netname: netpads[netname].append((ref,p[1],*transform(px,py)))
        cty=[]; fab=[]; silk=[]
        for g in f:
            if not isinstance(g,list) or not g[0].startswith('fp_'): continue
            layer=one(g,'layer',['layer',''])[1]
            if layer.endswith('CrtYd'):cty+=points(g)
            if layer.endswith('Fab'):fab+=points(g)
            if layer.endswith('SilkS'):silk+=points(g)
        extent=local+cty+fab+silk
        bbox=[min(p[0] for p in extent), min(p[1] for p in extent),max(p[0] for p in extent),max(p[1] for p in extent)] if extent else [0]*4
        fps.append(dict(ref=ref,value=prop.get('Value',''),footprint=f[1],x=x,y=y,rotation=math.degrees(ang),pads=len(pads),courtyard_vertices=len(cty),fab_vertices=len(fab),geometry_bbox=bbox,models=[m[1] for m in items(f,'model')],dnp=('dnp' in one(f,'attr',[]) or one(f,'dnp',['dnp','no'])[1]=='yes')))
    hpwl={n:round(max(p[2] for p in ps)-min(p[2] for p in ps)+max(p[3] for p in ps)-min(p[3] for p in ps),4) for n,ps in netpads.items() if len(ps)>1}
    edges=[g for g in b if isinstance(g,list) and g[0].startswith('gr_') and one(g,'layer',['layer',''])[1]=='Edge.Cuts']
    return dict(source=str(path),sha256=hashlib.sha256(raw.encode()).hexdigest(),footprint_count=len(fps),pad_count=sum(f['pads'] for f in fps),net_count=len(netpads),track_segments=len(items(b,'segment')),vias=len(items(b,'via')),zones=len(items(b,'zone')),outline_items=len(edges),copper_layers=[x[1] for x in one(b,'layers')[1:] if x[1].endswith('.Cu')],unverified_courtyards=[f['ref'] for f in fps if not f['courtyard_vertices']],footprints=fps,net_hpwl_mm=hpwl,total_hpwl_mm=round(sum(hpwl.values()),3),netpads=dict(netpads),validated_score=None,status='UNROUTED_INPUT' if not items(b,'segment') else 'NATIVE_VALIDATION_REQUIRED')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('board',type=Path);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    a=audit(args.board);args.out.write_text(json.dumps(a,indent=2)+'\n')
    print(json.dumps({k:v for k,v in a.items() if k not in ['footprints','netpads','net_hpwl_mm','unverified_courtyards']},indent=2));print('No courtyard:',len(a['unverified_courtyards']))
if __name__=='__main__':main()
