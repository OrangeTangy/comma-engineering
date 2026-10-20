#!/usr/bin/env python3
"""Estimate the PCBGolf score of a KiCad board and its assembly STEP.

Score = assembly bounding-box volume (mm^3) + 50 * vias + 5,000 * copper layers.

Needs OCP (cadquery-ocp) for the STEP measurement. Through-hole pads used only
to change layers also count as vias in the official review; this script counts
board vias only, so treat its number as a lower bound. It does not check DRC,
connectivity or any of the review rules, so an unrouted board has no real score.
"""
import argparse,json,re,sys
from pathlib import Path
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopoDS import TopoDS_Iterator
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

def board_counts(pcb):
    s=Path(pcb).read_text()
    layers=re.search(r'\n\t\(layers\n(.*?)\n\t\)',s,re.S).group(1)
    copper=len(re.findall(r'"[^"]+\.Cu" (?:signal|power|mixed|jumper)',layers))
    vias=len(re.findall(r'^\t\(via\b',s,re.M))
    tracks=len(re.findall(r'^\t\((?:segment|arc)\b',s,re.M))
    return copper,vias,tracks

def box(shape):
    b=Bnd_Box();BRepBndLib.Add_s(shape,b,True)
    lo,hi=b.CornerMin(),b.CornerMax()
    return (lo.X(),lo.Y(),lo.Z()),(hi.X(),hi.Y(),hi.Z())

def parts(shape,n=5):
    """Break the assembly into its components so the tallest ones can be named."""
    level=[shape]
    while len(level)<n:
        nxt=[]
        for x in level:
            it=TopoDS_Iterator(x)
            while it.More():nxt.append(it.Value());it.Next()
        if not nxt:break
        level=nxt
    return [box(p) for p in level]

ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('pcb',type=Path);ap.add_argument('step',type=Path);ap.add_argument('--json',type=Path)
a=ap.parse_args()
r=STEPControl_Reader()
if r.ReadFile(str(a.step))!=IFSelect_RetDone:sys.exit(f'cannot read {a.step}')
r.TransferRoots();shape=r.OneShape()
lo,hi=box(shape);dims=[h-l for l,h in zip(lo,hi)];volume=dims[0]*dims[1]*dims[2]
copper,vias,tracks=board_counts(a.pcb)
score=volume+50*vias+5000*copper
tall=sorted(parts(shape),key=lambda b:-b[1][2])[:5]
low=sorted(parts(shape),key=lambda b:b[0][2])[:3]
out=dict(pcb=str(a.pcb),step=str(a.step),dimensions_mm=[round(d,3) for d in dims],volume_mm3=round(volume,1),
    copper_layers=copper,vias=vias,track_segments=tracks,score_estimate=round(score),
    breakdown=dict(volume=round(volume),vias=50*vias,layers=5000*copper),
    tallest_parts_top_z=[round(b[1][2],2) for b in tall],lowest_parts_bottom_z=[round(b[0][2],2) for b in low],
    note='Lower bound: excludes layer-change through-hole pads; meaningless unless fully routed and DRC-clean.')
print(json.dumps(out,indent=2))
if a.json:a.json.write_text(json.dumps(out,indent=2)+'\n')
