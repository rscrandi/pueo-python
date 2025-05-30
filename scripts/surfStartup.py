from pueo.turf import PueoTURF
from pueo.turfio import PueoTURFIO
from pueo.surf import PueoSURF
import time
import sys

# WHATEVER JUST HARDCODE THIS FOR NOW
surfList = [ (0, 0) ]

dev = PueoTURF(None, 'Ethernet')
tio = {}
masks = {}
for surfAddr in surfList:
    if surfAddr[0] not in tio:
        print(f'Building TURFIO#{surfAddr[0]}')
        tio[surfAddr[0]] = PueoTURFIO((dev, surfAddr[0]), 'TURFGTP')
        print(f'TURFIO#{surfAddr[0]} : {tio[surfAddr[0]]}')
        masks[surfAddr[0]] = 0
    masks[surfAddr[0]] |= (1<<(surfAddr[1]+16))

for m in masks:
    print(f'mask {m} is {hex(masks[m])}')
    
# enable autotrain for the enabled SURFs
for n in tio:
    print(f'Setting TURFIO#{n} autotrain to {hex(masks[n])}')
    tio[n].surfturf.write(0x14, masks[n])

# enable RXCLK for the TURFIOs containing the SURFs
for t in tio.values():
    print(f'Enabling RXCLK on {t}')
    t.enable_rxclk(True)

surfActiveList = []
for surfAddr in surfList:
    tn = surfAddr[0]
    sn = surfAddr[1]
    # wait for train out rdy on each
    print(f'Waiting for train out rdy on SURF#{sn} on TURFIO#{tn}')
    loopno = 0
    while not(tio[tn].surfturf.read(0x18) & (1<<sn)) and loopno < 20:
        time.sleep(0.1)
    if loopno == 20:
        print(f'SURF#{sn} on TURFIO#{tn} did not become ready??')
    else:
        print(f'SURF#{sn} on TURFIO#{tn} is ready for out training')
        tio[tn].dalign[sn].trainEnable(False)
        surfActiveList.append(surfAddr)

# dumbass hackery
for surfAddr in surfActiveList:
    tn = surfAddr[0]
    sn = surfAddr[1]
    t = tio[tn]
    # THIS SHOULD BE AUTOSET?!?
    print(f'Applying sync offset to SURF#{sn} on TURFIO#{tn}')
    s = PueoSURF((t, sn), 'TURFIO')
    s.sync_offset = 7
    
print("Issuing SYNC")
dev.trig.runcmd(dev.trig.RUNCMD_SYNC)
trainedSurfs = []
for surfAddr in surfActiveList:
    tn = surfAddr[0]
    t = tio[tn]
    print(f'Training SURF#{sn} on TURFIO#{tn}:')
    eye = t.dalign[sn].find_alignment(doReset=True, verbose=True)
    if eye is not None:
        print(f'SURF#{sn} on TURFIO#{tn}: tap {eye[0]} offset {eye[1]}')
        t.dalign[sn].apply_alignment(eye, verbose=True)
        trainedSurfs.append(surfAddr)
    else:
        print(f'SURF#{sn} on TURFIO#{tn} failed training!!!')
        
print("Issuing NOOP_LIVE")
dev.trig.runcmd(dev.trig.RUNCMD_NOOP_LIVE)

for surfAddr in trainedSurfs:
    tn = surfAddr[0]
    sn = surfAddr[1]
    t = tio[tn]
    print(f'Unmasking data from SURF#{sn} on TURFIO#{tn}')
    t.dalign[sn].dout_mask = 0

