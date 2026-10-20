from run import simulate,check,feed
from reference import frame
import random,json
from pathlib import Path
R=random.Random(72026)
decls='''
reg start2=0; reg [10:0] id2=0; reg rtr2=0;
wire tx2,ready2,done2,lost2,err2; wire [2:0] code2;
reg ack_drive=1; integer loss2=0, success2=0;
can_tx other(clk,rst,drive_en,sample_en,start2,bus_bit,id2,rtr2,dlc,data,
 ready2,tx2,done2,lost2,err2,code2);
always @(negedge clk) begin if(lost2) loss2=loss2+1; if(done2) success2=success2+1; end
'''
code=[]; pairs=[]
for i in range(11): pairs.append((0,1<<i,0,0))
for _ in range(100):
 a,b=R.sample(range(2048),2); pairs.append((a,b,0,0))
pairs += [(0x123,0x123,0,1),(0x123,0x123,1,0)]
for n,(a,b,ra,rb) in enumerate(pairs):
 awins=(a,ra)<(b,rb); winner=a if awins else b
 code+=['start2=0; reset; loss2=0; success2=0;\n',f'identifier={a}; id2={b}; remote_frame={ra}; rtr2={rb}; dlc=1; data=64\'h5a00000000000000; start=1;start2=1;tick;start=0;start2=0;\n']
 code+=['repeat(160) begin drive_en=1;tick;drive_en=0; bus_bit=tx_bit & tx2 & ~ack_request; sample_en=1;tick;sample_en=0;tick;end\n']
 code+=[check(f'good==1 && bad==0 && id_out=={winner} && data_out==64\'h5a && sent=={int(awins)} && success2=={int(not awins)} && lost=={int(not awins)} && loss2=={int(awins)} && txbad==0',f'arbitration {n}')]
simulate('two_transmitters_wired_and', ''.join(code), decls)
# Single-node failure behavior. No automatic error flags claimed by these modules.
code=[]
for kind in ['no_ack','bit_error','invalid_dlc']:
 code+=['reset; identifier=123; dlc=1; data=64\'ha500000000000000;\n']
 if kind=='invalid_dlc':
  code+=['dlc=9;start=1;tick;start=0;tick;\n',check('txbad==1 && tx_code==1 && ready','invalid DLC')];continue
 code+=['start=1;tick;start=0;\n']
 w,ack,_=frame(123,b'\xa5')
 if kind=='no_ack': w[ack]=1
 else: w[0]=1
 for bit in w:
  code+=['drive_en=1;tick;drive_en=0;\n',f'sample({bit});\n']
 code+=[check(f'txbad==1 && sent==0 && tx_code=={2 if kind=="no_ack" else 3} && ready',kind)]
simulate('transmitter_faults',''.join(code))
Path(__file__).with_name('arbitration-results.json').write_text(json.dumps({'arbitration_cases':len(pairs),'transmitter_faults':3},indent=2)+'\n')
