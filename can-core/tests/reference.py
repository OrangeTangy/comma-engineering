"""Independent whole-frame oracle: CRC via integer polynomial long division.
Not a port of the sequential RTL CRC or its state machine.
"""
def bits(value, n):
    return [value >> i & 1 for i in reversed(range(n))]

def crc15(message):
    polynomial = 0xC599  # x^15 + x^14 + x^10 + x^8 + x^7 + x^4 + x^3 + 1
    dividend = int(''.join(map(str, message)), 2) << 15
    while dividend.bit_length() >= polynomial.bit_length():
        dividend ^= polynomial << (dividend.bit_length()-polynomial.bit_length())
    return dividend

def stuff(raw):
    out=[]; run=0; previous=None; inserted=[]
    for b in raw:
        out.append(b)
        run = run+1 if b==previous else 1
        previous=b
        if run==5:
            out.append(1-b); inserted.append(len(out)-1)
            previous=1-b; run=1
    return out, inserted

def frame(identifier, payload=b'', remote=False, dlc=None, bad_crc=False, ide=False):
    if dlc is None: dlc=len(payload)
    raw=[0]+bits(identifier,11)+[int(remote),int(ide),0]+bits(dlc,4)
    if not remote:
        for byte in payload: raw+=bits(byte,8)
    checksum=crc15(raw)^int(bad_crc)
    wire, inserted=stuff(raw+bits(checksum,15))
    ack_index=len(wire)+1
    wire += [1,0,1]+[1]*7+[1]*3
    return wire, ack_index, inserted
