"""Import a router session into a separate trial; requires KiCad Python."""
import argparse,shutil,pcbnew
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('session',type=Path);p.add_argument('destination',type=Path);a=p.parse_args()
assert a.source.resolve()!=a.destination.resolve()
shutil.copytree(a.source,a.destination,dirs_exist_ok=True)
b=pcbnew.LoadBoard(str(a.destination/'pcbgolf.kicad_pcb'))
assert pcbnew.ImportSpecctraSES(b,str(a.session)),'Router session import failed'
pcbnew.SaveBoard(str(a.destination/'pcbgolf.kicad_pcb'),b)
print('Imported for native verification; not a completed layout')
