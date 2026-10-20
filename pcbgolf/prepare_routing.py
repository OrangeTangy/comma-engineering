"""Run with KiCad's bundled Python. Prepare an experimental routing branch."""
from pathlib import Path
import json,sys,pcbnew,xml.etree.ElementTree as ET
root=Path(sys.argv[1]); path=root/'pcbgolf.kicad_pcb'
b=pcbnew.LoadBoard(str(path)); changes=[]
for f in b.GetFootprints():
 if f.GetReference()=='J3':
  f.ClearNetTiePadGroups()
  pads={p.GetNumber():p for p in f.Pads()}
  for n in ('B2','B3','B8','B10','B11'):
   assert pads[n].GetNetname().startswith('unconnected-')
   assert pads[n+'T'].GetNetname().startswith('unconnected-')
   # These pre-existing, overlapping pads represent one unused connector terminal.
   # Use one net for the same physical unused terminal, avoiding false shorts.
   pads[n+'T'].SetNet(pads[n].GetNet())
   changes.append({'reference':'J3','unused_terminal_pad_alias':[n,n+'T']})
# Explicit rectangle makes this step idempotent for the known placement trial.
for shape in b.GetDrawings():
 if shape.GetLayer()==pcbnew.Edge_Cuts:
  for getter,setter in [(shape.GetStart,shape.SetStart),(shape.GetEnd,shape.SetEnd)]:
   pt=getter();x=pcbnew.ToMM(pt.x);y=pcbnew.ToMM(pt.y)
   assert min(abs(x),abs(x+.2),abs(x-70),abs(x-70.2))<1e-5
   assert min(abs(y),abs(y+.2),abs(y-60),abs(y-60.2))<1e-5
   setter(pcbnew.VECTOR2I(pcbnew.FromMM(-.2 if x<35 else 70.2),pcbnew.FromMM(-.2 if y<30 else 60.2)))
# Optional integrated XML exported after integrate_schematics.py.
if len(sys.argv)>2:
 for net in ET.parse(sys.argv[2]).getroot().findall('./nets/net'):
  name=net.attrib['name']
  if not name.startswith('unconnected-'):continue
  for node in net.findall('node'):
   if node.attrib['ref'] not in ('U9','U10','U11','U12') or node.attrib['pin'] not in ('1','5','8'):continue
   fp=next(f for f in b.GetFootprints() if f.GetReference()==node.attrib['ref'])
   pad=next(p for p in fp.Pads() if p.GetNumber()==node.attrib['pin'])
   if pad.GetNetname()==name:continue
   assert pad.GetNetCode()==0
   ni=pcbnew.NETINFO_ITEM(b,name);b.Add(ni);pad.SetNet(ni)
for f in b.GetFootprints():
 if f.GetReference() in ('BH1','BH2','BH3','BH4','C6','C10','J4'):
  f.SetAttributes(f.GetAttributes() & ~pcbnew.FP_EXCLUDE_FROM_BOM)
pcbnew.SaveBoard(str(path),b)
pro=root/'pcbgolf.kicad_pro';p=json.loads(pro.read_text())
p['net_settings']['classes'][0]['clearance']=.15
p['erc']['rule_severities']['power_pin_not_driven']='error'
# NPTH-to-copper capability is 0.2 mm. PTH-to-track still requires explicit review.
p['board']['design_settings']['rules']['min_hole_clearance']=.2
p['board']['design_settings']['rules']['min_copper_edge_clearance']=.2
pro.write_text(json.dumps(p,indent=2)+'\n')
(root.parent/'routing-preparation.json').write_text(json.dumps({'changes':changes,'clearance_mm':.15,'hole_clearance_mm':.2,'copper_edge_clearance_mm':.2,'status':'EXPERIMENTAL_NOT_FAB_APPROVED','source':'https://jlcpcb.com/capabilities/pcb-capabilities/'},indent=2)+'\n')
