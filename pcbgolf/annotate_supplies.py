#!/usr/bin/env python3
"""Add source assertions for reviewed supply paths, without suppressing ERC.
Uses KiCad's PWR_FLAG symbol; external input power remains a design assumption.
"""
import sys,re,uuid,json
from pathlib import Path
from analyze import parse,items,one
root=Path(sys.argv[1]);library=Path(sys.argv[2])
def end(s,start):
 depth=0
 for m in re.finditer(r'"(?:\\.|[^"\\])*"|[()]',s[start:]):
  if m.group()=='(':depth+=1
  if m.group()==')':
   depth-=1
   if depth==0:return start+m.end()
 raise ValueError('unbalanced')
raw=library.read_text();m=re.search(r'\(symbol "PWR_FLAG"',raw);definition=raw[m.start():end(raw,m.start())].replace('PWR_FLAG','SUPPLY_SOURCE')
lib=root/'pcbgolf.kicad_sym';s=lib.read_text()
if '(symbol "SUPPLY_SOURCE"' not in s:s=s[:s.rfind(')')]+definition+'\n)\n';lib.write_text(s)
p=root/'power.kicad_sch';s=p.read_text();assert '#FLG901' not in s,'Already annotated'
libstart=s.index('(lib_symbols');libend=end(s,libstart)
s=s[:libend-1]+definition.replace('(symbol "SUPPLY_SOURCE"','(symbol "pcbgolf:SUPPLY_SOURCE"',1)+s[libend-1:]
tree=parse(s);inst=one(one(one(items(tree,'symbol')[0],'instances'),'project'),'path')[1]
sources=[('+5V','U2 switching output through L2'),('+3V3','U1 switching output through L1'),('+12V','external DC jack through reverse-protection Q1'),('GND','external DC jack return'),('VDDA','3.3 V through ferrite L3'),('VBUS','external USB host VBUS'),(None,'external DC jack input at J1.PWR1')]
insert=[]
for i,(net,reason) in enumerate(sources):
 x,y=(25.4+i*38.1,185.42) if net else (40.64,40.64)
 uid=str(uuid.uuid5(uuid.NAMESPACE_URL,'pcbgolf-supply-assertion-'+str(i)));ref=f'#FLG{901+i}'
 insert.append(f'''(symbol (lib_id "pcbgolf:SUPPLY_SOURCE") (at {x} {y} 0) (unit 1)
 (in_bom no) (on_board yes) (dnp no) (uuid "{uid}")
 (property "Reference" "{ref}" (at {x} {y+2.54} 0) (effects (font (size 1.27 1.27)) (hide yes)))
 (property "Value" "SUPPLY_SOURCE" (at {x} {y-5.08} 0) (effects (font (size 1.27 1.27))))
 (pin "1" (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,uid+'pin')}"))
 (instances (project "pcbgolf" (path "{inst}" (reference "{ref}") (unit 1)))))''')
 if net:
  insert.append(f'''(global_label "{net}" (shape input) (at {x} {y} 0)
 (effects (font (size 1.27 1.27)) (justify left))
 (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,uid+'label')}"))''')
s=s[:s.rfind(')')]+'\n'.join(insert)+'\n)\n';p.write_text(s)
(root.parent/'supply-assertions.json').write_text(json.dumps(dict(assertions=[dict(net=n or 'J1.PWR1',source=r) for n,r in sources],scope='Documents schematic supply paths only. Does not certify voltage, current, power sequencing, copper or hardware function.'),indent=2)+'\n')
