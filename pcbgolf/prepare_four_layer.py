#!/usr/bin/env python3
"""Create a four-layer routing experiment with a dedicated internal GND zone.
Run using KiCad Python. This does not establish impedance or thermal performance.
"""
from pathlib import Path
import argparse,shutil,json,pcbnew as p
ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('destination',type=Path);ap.add_argument('--dsn',type=Path,required=True);a=ap.parse_args()
assert a.source.resolve()!=a.destination.resolve()
shutil.copytree(a.source,a.destination,dirs_exist_ok=True)
b=p.LoadBoard(str(a.destination/'pcbgolf.kicad_pcb'))
assert len(list(b.GetTracks()))==0,'Use the unrouted critical trial'
b.SetCopperLayerCount(4)
ls=b.GetEnabledLayers();ls.AddLayer(p.In1_Cu);ls.AddLayer(p.In2_Cu);b.SetEnabledLayers(ls)
z=p.ZONE(b);z.SetLayer(p.In1_Cu);z.SetNet(b.FindNet('GND'));z.SetLocalClearance(p.FromMM(.2));z.SetMinThickness(p.FromMM(.15));z.SetPadConnection(p.ZONE_CONNECTION_FULL)
poly=z.Outline();poly.NewOutline()
for x,y in [(.05,.05),(69.95,.05),(69.95,59.95),(.05,59.95)]:poly.Append(p.FromMM(x),p.FromMM(y))
b.Add(z)
p.ZONE_FILLER(b).Fill(b.Zones())
p.SaveBoard(str(a.destination/'pcbgolf.kicad_pcb'),b)
assert p.ExportSpecctraDSN(b,str(a.dsn))
# Preserve the project's existing minimum trace constraint in router neck-down rules.
# Export does not encode this minimum: native DRC is mandatory after import.
print('Exported',a.dsn)
