#!/usr/bin/env python3
"""Run deterministic wire-level tests using Icarus Verilog. Python stdlib only."""
from pathlib import Path
import json, random, subprocess, tempfile, time
from reference import frame
ROOT=Path(__file__).resolve().parents[1]
R=random.Random(0xCA2026)

def simulate(name, body, declarations='', wiring=''):
    text='''`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg rst=1, sample_en=0, drive_en=0, start=0, bus_bit=1;
reg [10:0] identifier=0; reg remote_frame=0; reg [3:0] dlc=0; reg [63:0] data=0;
wire tx_bit,ready,done,arbitration_lost,tx_error; wire [2:0] tx_code;
can_tx tx(clk,rst,drive_en,sample_en,start,bus_bit,identifier,remote_frame,dlc,data,
 ready,tx_bit,done,arbitration_lost,tx_error,tx_code);
wire frame_valid,frame_error,rtr_out,ack_request,receiving; wire [2:0] rx_code;
wire [10:0] id_out; wire [3:0] dlc_out; wire [63:0] data_out;
can_rx rx(clk,rst,sample_en,bus_bit,frame_valid,frame_error,rx_code,
 id_out,rtr_out,dlc_out,data_out,ack_request,receiving);
integer good=0, bad=0, sent=0, lost=0, txbad=0;
integer last_error=0;
always @(negedge clk) begin
 if(frame_valid) good=good+1;
 if(frame_error) begin bad=bad+1; last_error=rx_code; end
 if(done) sent=sent+1;
 if(arbitration_lost) lost=lost+1;
 if(tx_error) txbad=txbad+1;
end
 task tick; begin @(posedge clk); #1; @(negedge clk); #1; end endtask
 task sample(input bit b); begin bus_bit=b; sample_en=1; tick; sample_en=0; tick; end endtask
 task reset; begin rst=1; sample_en=0; drive_en=0; start=0; tick; rst=0;
 repeat(11) sample(1); good=0;bad=0;sent=0;lost=0;txbad=0;last_error=0; end endtask
''' + declarations + wiring + '\ninitial begin\n' + body + '\n$display("PASS '+name+'"); $finish; end\ninitial begin #1000000000; $fatal(1,"watchdog"); end\nendmodule\n'
    with tempfile.TemporaryDirectory(prefix='can-test-') as tmp:
        p=Path(tmp); (p/'tb.sv').write_text(text)
        cmd=['iverilog','-g2012','-Wall','-s','tb','-o',str(p/'sim'),str(p/'tb.sv')]+[str(x) for x in sorted((ROOT/'rtl').glob('*.sv'))]
        c=subprocess.run(cmd,capture_output=True,text=True)
        if c.returncode: raise RuntimeError(c.stderr)
        result=subprocess.run(['vvp',str(p/'sim')],capture_output=True,text=True,timeout=120)
        if result.returncode:
            (ROOT/'tests'/'FAILED_tb.sv').write_text(text)
            raise AssertionError(result.stdout+result.stderr)
        print(result.stdout.strip())

def feed(wire): return ''.join(f'sample({b});' for b in wire)+'\n'
def check(cond,label): return f'if(!({cond})) $fatal(1,"{label}");\n'

def main():
    t=time.monotonic(); counts={}
    cases=[]
    for d in range(9):
        for ident in [0,1,0x155,0x555,0x7fe,0x7ff]:
            for byte in [0,255,0xaa,0x55]: cases.append((ident,bytes([byte]*d),False,d))
            cases.append((ident,b'',True,d))
    for _ in range(500):
        d=R.randrange(9); cases.append((R.randrange(2048),R.randbytes(d),False,d))
    # Reserved receive DLC codes represent eight data bytes.
    rx_cases=cases+[(123,R.randbytes(8),False,d) for d in range(9,16)]
    code=[]
    boundary=0
    for n,(ident,payload,remote,d) in enumerate(rx_cases):
        wire,ack,ins=frame(ident,payload,remote,d)
        boundary+=bool(ins and ins[-1]==ack-2)
        code+=['reset;\n',feed(wire[:ack]),check('ack_request',f'RX ACK {n}'),feed(wire[ack:])]
        value=int.from_bytes(payload,'big') if not remote else 0
        code+=[check(f'good==1 && bad==0 && id_out=={ident} && rtr_out=={int(remote)} && dlc_out=={d} && data_out==64\'h{value:016x}',f'RX frame {n}')]
    simulate('receive_valid', ''.join(code)); counts['receive_valid']=len(rx_cases); counts['crc_end_stuff_cases']=boundary
    code=[]
    for n,(ident,payload,remote,d) in enumerate(cases):
        wire,ack,_=frame(ident,payload,remote,d)
        val=int.from_bytes(payload.ljust(8,b'\0'),'big')
        code+=['reset;\n',f'identifier={ident}; remote_frame={int(remote)}; dlc={d}; data=64\'h{val:016x}; start=1; tick; start=0;\n']
        for i,b in enumerate(wire):
            expected=1 if i==ack else b
            code+=['drive_en=1; tick; drive_en=0;\n',check(f'tx_bit=={expected}',f'TX {n} bit {i}'),f'sample({b});\n']
        code+=[check('sent==1 && txbad==0 && lost==0 && ready',f'TX complete {n}')]
    simulate('transmit_oracle', ''.join(code)); counts['transmit_oracle']=len(cases)
    code=[]; faults=0
    for n in range(100):
        ident=R.randrange(2048); payload=R.randbytes(R.randrange(9))
        for kind in ['crc','stuff','delimiter','eof','ide']:
            w,ack,ins=frame(ident,payload,bad_crc=kind=='crc',ide=kind=='ide')
            err={'crc':2,'stuff':1,'delimiter':3,'eof':3,'ide':4}[kind]
            if kind=='stuff':
                if not ins: continue
                w[ins[0]]=w[ins[0]-1]
            if kind=='delimiter': w[ack-1]=0
            if kind=='eof': w[ack+2]=0
            code+=['reset;\n',feed(w),check(f'good==0 && bad>=1 && last_error=={err}',f'fault {kind} {n}')]
            # Recovery must permit a subsequent good frame without reset.
            code+=['repeat(11) sample(1);\n',feed(frame(42,b'\x13\x37')[0]),check('good==1 && id_out==42 && data_out==64\'h1337',f'recovery {kind} {n}')]
            faults+=1
    simulate('receive_faults_and_recovery',''.join(code)); counts['receive_faults_and_recovery']=faults
    # Back-to-back frames at exactly three intermission bits, no extra idle/reset.
    code=['reset;\n']
    for n in range(100): code += [feed(frame(n,bytes([n]))[0]),check(f'good=={n+1} && bad==0',f'back-to-back {n}')]
    simulate('back_to_back',''.join(code)); counts['back_to_back']=100
    # Reset in every phase of a maximum length frame.
    w=frame(0,b'\0'*8)[0]; code=[]
    for cut in range(len(w)):
        code+=['reset;\n',feed(w[:cut]),'reset;\n',feed(frame(0x456,b'\x55')[0]),check('good==1 && bad==0 && id_out==1110','reset recovery')]
    simulate('reset_every_bit',''.join(code)); counts['reset_every_bit']=len(w)
    counts['seconds']=round(time.monotonic()-t,3)
    (ROOT/'tests'/'results.json').write_text(json.dumps(counts,indent=2)+'\n')
    print(json.dumps(counts,indent=2))
if __name__=='__main__': main()
