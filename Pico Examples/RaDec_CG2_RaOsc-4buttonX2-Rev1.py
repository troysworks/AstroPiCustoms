import machine
import utime

Rapins = [ 6, 7, 8, 9 ]
Decpins = [ 10, 11, 12, 13 ]
stepmatrix = [ [ 1, 0, 1, 0 ], [ 0, 1, 1, 0 ], [ 0, 1, 0, 1 ], [ 1, 0, 0, 1 ] ]
for n in range(0, 4):
    machine.Pin(Rapins[n], machine.Pin.OUT)
    machine.Pin(Rapins[n]).value(0)
    machine.Pin(Decpins[n], machine.Pin.OUT)
    machine.Pin(Decpins[n]).value(0)

RaE = machine.Pin(21, machine.Pin.IN, machine.Pin.PULL_DOWN)
RaW = machine.Pin(20, machine.Pin.IN, machine.Pin.PULL_DOWN)
DecN = machine.Pin(19, machine.Pin.IN, machine.Pin.PULL_DOWN)
DecS = machine.Pin(18, machine.Pin.IN, machine.Pin.PULL_DOWN)
X2Speed = machine.Pin(17, machine.Pin.IN, machine.Pin.PULL_DOWN)

#Delay = .15 # 96Tooth worm .1565 - overhead time
Delay = .107 # 144Tooth worm 
XDelay = Delay / 2
RaCount = 0
DecCount = 0

while True:
    if X2Speed.value() == 1:
        XDelay = Delay / 2
    else:
        XDelay = Delay / 8
            
    while RaE.value() == 1:  # East
        RaCount -= 1
        if RaCount < 0:
            RaCount = 3
        for n in range(0, 4): # All Off
            machine.Pin(Rapins[n]).value(0)
        for n in range(0, 4):
            machine.Pin(Rapins[n]).value(stepmatrix[RaCount][n])
        utime.sleep(XDelay)
        #print("East")
    
    while RaW.value() == 1:  # West
        RaCount += 1
        if RaCount > 3:
            RaCount = 0
        for n in range(0, 4): # All Off
            machine.Pin(Rapins[n]).value(0)
        for n in range(0, 4):
            machine.Pin(Rapins[n]).value(stepmatrix[RaCount][n])
        utime.sleep(XDelay)
        #print("West")
        
    while DecS.value() == 1:  # South
        DecCount -= 1
        if DecCount < 0:
            DecCount = 3
        for n in range(0, 4): # All Off
            machine.Pin(Decpins[n]).value(0)
        for n in range(0, 4):
            machine.Pin(Decpins[n]).value(stepmatrix[DecCount][n])
        utime.sleep(XDelay)
        #print("South")
        
    while DecN.value() == 1:  # North
        DecCount += 1
        if DecCount > 3:
            DecCount = 0
        for n in range(0, 4): # All Off
            machine.Pin(Decpins[n]).value(0)
        for n in range(0, 4):
            machine.Pin(Decpins[n]).value(stepmatrix[DecCount][n])
        utime.sleep(XDelay)
        #print("North")
    
    #Ra West
    RaCount += 1
    if RaCount > 3:
        RaCount = 0
    for n in range(0, 4): # All Off
        machine.Pin(Rapins[n]).value(0)
    for n in range(0, 4):
        machine.Pin(Rapins[n]).value(stepmatrix[RaCount][n])

    utime.sleep(Delay)
