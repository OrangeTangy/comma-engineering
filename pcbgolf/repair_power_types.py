#!/usr/bin/env python3
"""Correct only documented output pin electrical types in embedded/project symbols.
No wire, net, pin number, component value or connection is changed.
"""
import re,json,sys
from pathlib import Path
root=Path(sys.argv[1]);changes=[]
rules={'STM32H725ZGTx':{'15':'power_out'},'comma.ai_11112255_TPS25942':{'4':'power_out','5':'passive','6':'passive','7':'passive','8':'passive'},'comma.ai_11112255_USB-C-FEMALEGCT':{k:'passive' for k in ('A4','A9','B4','B9')}}
rules.update({
 'comma.ai_11112255_USB-C-FEMALEGCT':{'*':'passive'},
 'comma.ai_11112255_USB-C-FEMALE':{'*':'passive'},
 'comma.ai_11112255_CRYSTAL-4PIN4-PIN':{'*':'passive'},
 'comma.ai_11112255_CREE-RGB-CLMVC':{'*':'passive'},
 'comma.ai_11112255_USB2517':{'19':'input','25':'power_out','62':'power_out'},
 'comma.ai_11112255_MCP2542FDT-E/MNY':{'5':'power_in'},
})
def end(s,start):
 depth=0
 for m in re.finditer(r'"(?:\\.|[^"\\])*"|[()]',s[start:]):
  t=m.group()
  if t=='(':depth+=1
  if t==')':
   depth-=1
   if depth==0:return start+m.end()
 raise ValueError('unbalanced expression')
for path in list(root.glob('*.kicad_sch'))+[root/'pcbgolf.kicad_sym']:
 s=path.read_text();edits=[]
 for symbol,pins in rules.items():
  for m in re.finditer(r'\(symbol "(?:pcbgolf:)?'+re.escape(symbol)+r'"',s):
   hi=end(s,m.start());block=s[m.start():hi]
   for pm in re.finditer(r'\(pin (power_in|power_out|passive|bidirectional)\b',block):
    ph=end(block,pm.start());pinblock=block[pm.start():ph]
    num=re.search(r'\(number "([^"]+)"',pinblock).group(1)
    if num not in pins and '*' not in pins:continue
    old=pm.group(1);new=pins.get(num,pins.get('*'))
    if old==new:continue
    lo=m.start()+pm.start()+len('(pin ');edits.append((lo,lo+len(old),new))
    changes.append(dict(file=path.name,symbol=symbol,pin=num,from_type=old,to_type=new))
 for lo,hi,v in sorted(edits,reverse=True):s=s[:lo]+v+s[hi:]
 path.write_text(s)
(root.parent/'power-type-repair.json').write_text(json.dumps(dict(final_rules=rules,changes=changes,sources=['https://www.st.com/resource/en/datasheet/stm32h725ve.pdf','https://www.ti.com/lit/gpn/TPS25942A','https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/USB2517-USB2517i-Data-Sheet-00001598C.pdf','https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP2542FD-MCP2542WFD-4WFD-Data-Sheet-DS20005514C.pdf'],rationale='VLXSMPS is the internal converter switching output; TPS25942 OUT pins are the switched supply output. Pin 4 represents the driver; internally common pins 5-8 are passive to avoid falsely modeling five independent supplies. USB2517 pins 25/62 represent its internal 1.8 V regulators; TEST is an input. MCP2542 VIO is a supply input. Connectors, crystals and LEDs are passive. Electrical-type annotation only; does not certify circuit function.'),indent=2)+'\n')
print('Updated',len(changes),'pin type declarations')
