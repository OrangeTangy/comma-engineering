#!/usr/bin/env python3
"""Create golf-v2/: the low-profile connector redesign of the four-layer trial's schematic.

- J5-J8 (OBD-C ports): vertical Amphenol 10132328 -> horizontal JAE DX07S024XJ1R1100,
  the 24-pin receptacle the original design already uses for the host port J3.
  Pad numbers are renamed to the vertical symbol's pins so the netlist is unchanged.
- BH1-BH4 (DNP M2 holes, optional per commaai/PCBGolf#5) are taken off the board.
- J1 (12 V input): top-mount PJ-002AH-SMT-TR (11.0 mm above the board) -> mid-mount
  PJ-107AH-MSMT-TR, which takes the same 5.5 / 2.0 mm plug and sits in a board notch.
  Footprint from the Same Sky datasheet (2024-09-25), 3D model from Same Sky's CAD service.

Run with Python 3: make_golf_v2.py SOURCE_PROJECT DESTINATION JACK_STEP
The PCB is rebuilt afterwards by place_golf_v2.py (KiCad Python).
"""
import argparse,json,re,shutil,uuid
from pathlib import Path

def u():return str(uuid.uuid4())

def obdc_footprint(dx07):
    """DX07 footprint with pads renumbered to the vertical OBD-C symbol's pins."""
    s=dx07.replace('(footprint "DX07S024XJ1R1100"','(footprint "DX07S024XJ1R1100_OBDC"',1)
    s=s.replace('(property "Value" "DX07S024XJ1R1100"','(property "Value" "DX07S024XJ1R1100_OBDC"',1)
    s=re.sub(r'\(pad "B(\d+)T"',r'(pad "B\1"',s)
    s=re.sub(r'\(pad "S(\d)(?:TH|T)"',r'(pad "S\1"',s)
    s=re.sub(r'\(pad "S(\d)B"',r'(pad "S1\1"',s)
    # The upstream footprint has no courtyard; outline the body (fab line at y=8.85 is the mating face).
    crt=''.join(f'\t(fp_line (start {a} {b}) (end {c} {d}) (stroke (width 0.05) (type solid)) (layer "F.CrtYd") (uuid "{u()}"))\n'
        for a,b,c,d in [(-5.0,-1.5,5.0,-1.5),(5.0,-1.5,5.0,8.9),(5.0,8.9,-5.0,8.9),(-5.0,8.9,-5.0,-1.5)])
    i=s.index('\t(pad ');return s[:i]+crt+s[i:]

def line(a,b,c,d,layer,w):
    return f'\t(fp_line (start {a} {b}) (end {c} {d}) (stroke (width {w}) (type solid)) (layer "{layer}") (uuid "{u()}"))\n'

def oval(num,x,y,w,h,dw,dh):
    return (f'\t(pad "{num}" thru_hole oval (at {x} {y}) (size {w} {h}) (drill oval {dw} {dh}) '
            f'(layers "*.Cu" "*.Mask") (remove_unused_layers no) (uuid "{u()}"))\n')

def jack_footprint():
    """PJ-107AH-MSMT-TR. Origin = centre pin; +y points to the board edge the plug enters from.

    Datasheet: centre pin dia 1.4 hole / 2.4 pad; terminals 2 and 3 at x -7.15 / +5.45,
    2.8 mm toward the edge; shell legs at x -7.4 / +5.7, 3.05 mm from the board edge;
    the edge is 12.6 mm from the centre pin (front face overhangs 1.2 mm);
    body notch x -6.0..+4.3 from y 1.9 to the edge. The notch itself is drawn on
    Edge.Cuts by the board script so that it merges with the outline.
    """
    s=f'''(footprint "PJ-107AH-MSMT"
\t(version 20260206)
\t(generator "make_golf_v2")
\t(layer "F.Cu")
\t(descr "Same Sky PJ-107AH-MSMT-TR mid-mount DC jack, 2.0 mm centre pin, 5.5 mm plug; needs board notch")
\t(property "Reference" "REF**" (at 0 -2.5 0) (layer "F.SilkS") (uuid "{u()}") (effects (font (size 0.8 0.8) (thickness 0.12))))
\t(property "Value" "PJ-107AH-MSMT" (at 0 8 0) (layer "F.Fab") (uuid "{u()}") (effects (font (size 0.8 0.8) (thickness 0.12))))
\t(property "Datasheet" "https://www.sameskydevices.com/product/resource/pj-107ah-msmt-tr.pdf" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{u()}") (effects (font (size 1 1))))
\t(property "Description" "" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{u()}") (effects (font (size 1 1))))
\t(attr through_hole)
'''
    for a,b,c,d in [(-5.85,0.0,4.15,0.0),(4.15,0.0,4.15,13.8),(4.15,13.8,-5.85,13.8),(-5.85,13.8,-5.85,0.0)]:
        s+=line(a,b,c,d,'F.Fab',0.1)
    for a,b,c,d in [(-8.4,-1.4,6.7,-1.4),(6.7,-1.4,6.7,13.9),(6.7,13.9,-8.4,13.9),(-8.4,13.9,-8.4,-1.4)]:
        s+=line(a,b,c,d,'F.CrtYd',0.05)
    for a,b,c,d in [(-6.0,12.6,-6.0,1.9),(-6.0,1.9,4.3,1.9),(4.3,1.9,4.3,12.6)]:
        s+=line(a,b,c,d,'Dwgs.User',0.1)
    s+=f'\t(pad "PWR1" thru_hole circle (at 0 0) (size 2.4 2.4) (drill 1.4) (layers "*.Cu" "*.Mask") (remove_unused_layers no) (uuid "{u()}"))\n'
    s+=oval('GND',-7.15,2.8,1.7,2.9,0.8,2.0)
    s+=oval('GNDBREAK',5.45,2.8,1.7,2.3,0.8,1.4)
    s+=oval('GND',-7.4,9.55,2.0,3.0,1.0,2.0)
    s+=oval('GND',5.7,9.55,2.0,3.0,1.0,2.0)
    # Model: native Y is vertical (flange plane at Y=-0.9), +Z is the plug face; the KiCad offset
    # y=+0.3 puts the face 1.2 mm past the board edge as the datasheet layout shows (checked in STEP).
    s+='''\t(model "${KIPRJMOD}/pcbgolf.3dshapes/Connector_BarrelJack.3dshapes/PJ-107AH-MSMT-TR.step"
\t\t(offset (xyz 0 0.3 0.9))
\t\t(scale (xyz 1 1 1))
\t\t(rotate (xyz 90 0 0))
\t)
)
'''
    return s

def symbol_block(text,ref):
    i=text.index(f'(property "Reference" "{ref}"')
    start=text.rfind('\n\t(symbol',0,i);end=text.find('\n\t(symbol',i)
    return start,len(text) if end<0 else end

def set_prop(text,ref,prop,old,new,required=True):
    """Replace one property value on the symbol instance whose Reference is ref."""
    i=text.index(f'(property "Reference" "{ref}"')
    start=text.rfind('\n\t(symbol',0,i);end=text.find('\n\t(symbol',i)
    end=len(text) if end<0 else end
    block=text[start:end];new_block=block.replace(f'(property "{prop}" "{old}"',f'(property "{prop}" "{new}"',1)
    assert new_block!=block or not required,(ref,prop,old)
    return text[:start]+new_block+text[end:]

ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('destination',type=Path);ap.add_argument('jack_step',type=Path)
a=ap.parse_args()
assert not a.destination.exists(),'destination exists'
shutil.copytree(a.source,a.destination,ignore=shutil.ignore_patterns('*.kicad_prl','*.lck','*-backups'))
lib=a.destination/'pcbgolf.pretty'
(lib/'DX07S024XJ1R1100_OBDC.kicad_mod').write_text(obdc_footprint((lib/'DX07S024XJ1R1100.kicad_mod').read_text()))
(lib/'PJ-107AH-MSMT.kicad_mod').write_text(jack_footprint())
for old in ('USB-C-FEMALE-VERT-GCT','DCJACK_2MM_SMT'):(lib/f'{old}.kicad_mod').unlink()
shapes=a.destination/'pcbgolf.3dshapes'
shutil.copy(a.jack_step,shapes/'Connector_BarrelJack.3dshapes/PJ-107AH-MSMT-TR.step')
for old in ('Connector_BarrelJack.3dshapes/PJ-002AH-SMT-TR.step','Connector_USB.3dshapes/10132328-10011LF.step'):
    (shapes/old).unlink()

sch=a.destination/'pcbgolf_5.kicad_sch';t=sch.read_text()
for ref in ('J5','J6','J7','J8'):
    t=set_prop(t,ref,'Footprint','pcbgolf:USB-C-FEMALE-VERT-GCT','pcbgolf:DX07S024XJ1R1100_OBDC')
    t=set_prop(t,ref,'MPN','10132328-10011LF','DX07S024XJ1R1100',required=False)
sch.write_text(t)
sch=a.destination/'power.kicad_sch';t=sch.read_text()
t=set_prop(t,'J1','Footprint','pcbgolf:DCJACK_2MM_SMT','pcbgolf:PJ-107AH-MSMT')
t=set_prop(t,'J1','MPN','PJ-002AH-SMT-TR','PJ-107AH-MSMT-TR')
# DNP M2 mounting holes are optional (commaai/PCBGolf#5); take them off the board.
for ref in ('BH1','BH2','BH3','BH4'):
    i,j=symbol_block(t,ref);blk=t[i:j].replace('(on_board yes)','(on_board no)',1).replace('(in_bom yes)','(in_bom no)',1)
    t=t[:i]+blk+t[j:]
sch.write_text(t)
# JLCPCB standard 2-layer capability with margin, and power net classes. Widths assume 1 oz
# outer copper: each port eFuse limits at 3.06 A (0.8 mm); the 12 V input/trunk feeds all four (1.2 mm).
pro=a.destination/'pcbgolf.kicad_pro';cfg=json.loads(pro.read_text())
cfg['board']['design_settings']['rules'].update(min_clearance=0.127,min_track_width=0.127,min_via_diameter=0.6,
    min_through_hole_diameter=0.3,min_via_annular_width=0.099,min_hole_clearance=0.25,min_hole_to_hole=0.25,
    min_copper_edge_clearance=0.3)
base=cfg['net_settings']['classes'][0]
base.update(track_width=0.15,clearance=0.15,via_diameter=0.6,via_drill=0.3)
def cls(name,width,prio):return {**base,'name':name,'track_width':width,'clearance':0.15,'priority':prio}
cfg['net_settings']['classes']=[base,cls('HighCurrent',1.2,0),cls('PortPower',0.8,1),cls('Power',0.4,2)]
pat=[('HighCurrent','+12V'),('HighCurrent','Net-(J1-PWR)')]+[('PortPower',f'Net-(J{i}-VBUS-PadA4)') for i in (5,6,7,8)]
pat+=[('Power',n) for n in ('+5V','+3V3','GND','VBUS','VDDLDO','VLXSMPS','Net-(U1-SW)','Net-(U2-SW)')]
cfg['net_settings']['netclass_patterns']=[{'netclass':c,'pattern':n} for c,n in pat]
pro.write_text(json.dumps(cfg,indent=2)+'\n')
print('created',a.destination)
