#!/usr/bin/env python3
"""Specctra round trip for golf-v2. Run with KiCad's bundled Python.

  route_golf_v2.py export golf-v2 board.dsn [LAYERS]  # net classes come from pcbgolf.kicad_pro
  route_golf_v2.py import golf-v2 board.ses [LAYERS]  # imports tracks/vias, then adds GND pours

LAYERS is 2 (default) or 4; with 4, In1.Cu is a solid GND plane and In2.Cu carries signals.

Route in between with Freerouting, for example:
  java -jar freerouting.jar -de board.dsn -do board.ses -mp 100 --gui.enabled=false
"""
import pcbnew as p,sys
from pathlib import Path
mode,project,path=sys.argv[1],Path(sys.argv[2]),sys.argv[3]
layers=int(sys.argv[4]) if len(sys.argv)>4 else 2
pcb=str(project/'pcbgolf.kicad_pcb');b=p.LoadBoard(pcb)
keep=[]
if layers==4:
    b.SetCopperLayerCount(4);ls=b.GetEnabledLayers();ls.AddLayer(p.In1_Cu);ls.AddLayer(p.In2_Cu);b.SetEnabledLayers(ls)
def gnd_pours():
    """GND pour on both layers over the whole outline. Pads connect with thermal relief."""
    outline=p.SHAPE_POLY_SET();assert b.GetBoardPolygonOutlines(outline,False)
    for z in list(b.Zones()):keep.append(z);b.Remove(z)
    for layer in (p.F_Cu,p.B_Cu)+((p.In1_Cu,) if layers==4 else ()):
        z=p.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('GND'));z.SetIsFilled(False)
        z.SetLocalClearance(p.FromMM(0.2));z.SetMinThickness(p.FromMM(0.2))
        z.SetPadConnection(p.ZONE_CONNECTION_THERMAL);z.SetThermalReliefGap(p.FromMM(0.2))
        z.SetThermalReliefSpokeWidth(p.FromMM(0.3));z.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS)
        z.Outline().Append(outline);b.Add(z);keep.append(z)
if mode=='export':
    # The pours tell Freerouting to treat GND as plane-connected rather than routing it as traces.
    gnd_pours();assert p.ExportSpecctraDSN(b,path);print('exported',path)
    sys.exit()
assert mode=='import'
assert p.ImportSpecctraSES(b,path)
gnd_pours()
p.ZONE_FILLER(b).Fill(b.Zones())
p.SaveBoard(pcb,b)
vias=sum(1 for t in b.GetTracks() if t.Type()==p.PCB_VIA_T)
print('imported',path,'vias',vias,'tracks',sum(1 for t in b.GetTracks())-vias)
