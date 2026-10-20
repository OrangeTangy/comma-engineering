"""Join the five supplied standalone drawings into one KiCad hierarchy.
Preserves symbols/wires/global labels. Repairs symbol instance and PCB sheet paths.
"""
import re,uuid,sys,json
from pathlib import Path
from analyze import parse,items,one
root=Path(sys.argv[1]);topid=str(uuid.uuid5(uuid.NAMESPACE_URL,'pcbgolf-integrated-root'))
sources=[('Power','power.kicad_sch'),('Microcontroller','pcbgolf_2.kicad_sch'),('USB_SD','pcbgolf_3.kicad_sch'),('CAN','pcbgolf_4.kicad_sch'),('Ports','pcbgolf_5.kicad_sch')]
if not (root/'power.kicad_sch').exists():(root/'power.kicad_sch').write_bytes((root/'pcbgolf.kicad_sch').read_bytes())
sheets=[];refpaths={}
for i,(name,file) in enumerate(sources):
 sid=str(uuid.uuid5(uuid.NAMESPACE_URL,'pcbgolf-sheet-'+name));instance=f'/{topid}/{sid}'
 p=root/file;s=p.read_text();tree=parse(s)
 for sym in items(tree,'symbol'):
  props={x[1]:x[2] for x in items(sym,'property')};ref=props['Reference']
  if not ref.startswith('#'):refpaths[ref]=f'/{sid}/'+one(sym,'uuid')[1]
 # These standalone files use one old root path for every symbol instance.
 oldpaths={one(one(one(sym,'instances'),'project'),'path')[1] for sym in items(tree,'symbol')}
 for old in oldpaths:s=s.replace(f'(path "{old}"',f'(path "{instance}"')
 p.write_text(s)
 x=25+(i%2)*110;y=30+(i//2)*45
 sheets.append(f'''(sheet (at {x} {y}) (size 85 30) (fields_autoplaced yes)
 (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid "{sid}")
 (property "Sheetname" "{name}" (at {x} {y-1} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
 (property "Sheetfile" "{file}" (at {x} {y+31} 0) (effects (font (size 1.27 1.27)) (justify left top)))
 (instances (project "pcbgolf" (path "/{topid}" (page "{i+2}")))))''')
(root/'pcbgolf.kicad_sch').write_text(f'''(kicad_sch (version 20260306) (generator "eeschema") (generator_version "10.0")
 (uuid "{topid}") (paper "A4") (lib_symbols)
 {''.join(sheets)}
 (sheet_instances (path "/" (page "1"))) (embedded_fonts no))\n''')
bp=root/'pcbgolf.kicad_pcb';s=bp.read_text();matches=list(re.finditer(r'^\t\(footprint\b',s,re.M));changes=[]
for i,m in enumerate(matches):
 end=matches[i+1].start() if i+1<len(matches) else len(s);chunk=s[m.start():end]
 ref=re.search(r'\(property "Reference" "([^"]+)"',chunk).group(1)
 path=re.search(r'\(path "[^"]+"\)',chunk)
 assert ref in refpaths,ref
 changes.append((m.start()+path.start(),m.start()+path.end(),f'(path "{refpaths[ref]}")'))
for lo,hi,v in reversed(changes):s=s[:lo]+v+s[hi:]
bp.write_text(s)
(root.parent/'hierarchy-repair.json').write_text(json.dumps({'root_uuid':topid,'sheets':sources,'footprint_paths_updated':len(changes),'electrical_wires_modified':False,'global_labels_modified':False},indent=2)+'\n')
print('Integrated',len(sources),'sheets;',len(changes),'footprint paths')
