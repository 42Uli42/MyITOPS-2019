#Sternfeuerung 1.0 Beta
#python program to be runned on the controler side
#version 3
#University of applied science Karlsruhe (HsKa) and Universiti Malaysia Pahang (UMP)
#MyITOPS: International Team Oriented Project Studies
#in the field of cyberphysical Systems
#SoSe 2019
#batch one
#HsKa students:
#Lorenz-Leo Wilhelm
#Uli Michael Hochreither
#Jakob Kleikamp
#UMP students:
#Nurain Binti Rozy
#Muhammad Syakir Bin Turiman
#Muhammad Nor Azril Bin Zulkafli

#=======================imports==============================#
import time, threading
from pylsl import StreamInlet, resolve_stream, StreamInfo, StreamOutlet
import pigpio
import obd

#=======================global parameters==============================#
FEEDBACK_DATA = 10      #number of feedback data from OBD
FEEDBACK_SAMPLE = 1     #time in s how often feedback data from OBD will be sent
CONTROLINTERVAL = 0.1   #time how fast the controler runs
SERVOLIMITLOW = 0       #min value in deg how far the servo is allowed to move
SERVOLIMITHIGH = 165    #max value in deg how far the servo is allowed to move

#=======================global variables==============================#
LIMITCALIBHIGH = 0      #servo angle where the throttle pedal is at its maximum value (100%)
LIMITCALIBLOW = 0       #servo angle where the throttle pedal is at its minimum value (0%)
pfactor = 0.0           #value to tune the pi controller recieved by the operator, p-value, linear part of the pi-equation
ifactor = 0.0           #value to tune the pi controller recieved by the operator, i-value, integral part of the pi-equation
cycletime = None        #value to store the time the program took to run

timevalue=0.0

cSPEED=0.0              #value of current speed
cRPM=0.0                #value of current RPM
cENGINE_LOAD=0.0        #value of current engine load
cCOMMANDED_EQUIV_RATIO=0.0  #value of current commanded equivalent ratio
cCOOLANT_TEMP=0.0       #value of current coolant temperature
cTIMING_ADVANCE=0.0     #value of current timing advance
cINTAKE_TEMP=0.0        #value of current air intake temperature
cMAF=0.0                #value of current Lambda
cRELATIVE_THROTTLE_POS=0.0  #current relative throttle position
P = 0.0         #P gain of controller
I = 0.0         #I gain of controller

control_mode=0      #control mode to be transmitted by the operator
target_speed=0      #target speed to be transmitted by the operator
throttle=0          #target throttle to be transmitted by the operator
indata=0.0          #value for recieved Data from operator
readallobd = False  #flag if feedback data should be requested in this cycle
obdfinish = False   #flag if obd device is currently reading data from car
lookup = [0] * 65   #lookup table: throttle value --> servo angle

#=======================initial settings==============================#
pi = pigpio.pi()    #attaching Servo
print("Servo connected")

#setup reading from OBD device
print("Connecting to OBD...")
connection = obd.OBD()
print("Successfully connected")

#setup sending information back to PC
#stream name: backstream, content-type: backstream, number of channels (how many values peer sample): here parameter FEEDBACK_DATA, frequency: 100 Hz, Datatype: float32, auto-reconnect identifyer: not configured here
info = StreamInfo('backstream', 'backstream', FEEDBACK_DATA, 100, 'float32', '1')
outlet = StreamOutlet(info)

#setup receiving data from PC
print("Looking for an input stream")
streams = resolve_stream('type', 'operator')    #second argument is the name of the stream from the operator
inlet = StreamInlet(streams[0])
print("Stream found")

#=======================functions==============================#
def calibration():      #finds the full throttle and zero throttle position and creates the lookup table: throttle value --> servo angle
    global SERVOLIMITHIGH, SERVOLIMITLOW, LIMITCALIBHIGH, LIMITCALIBLOW, lookup
    print("now calibrating")
    moveServo(70)       #moves the servo to a high position
    time.sleep(0.5)     #waits 0.5 seconds that the system is stationary
    if (connection.query(obd.commands.RELATIVE_THROTTLE_POS).value.magnitude > 0.0):    #if the OBD throttle position is not zero 
        i = 70      #maximum value of degree the servo will move
        while (True):   #endless loop, exited by break
            moveServo(i)    #moves the servo to i
            i -= 1          #one degree less next loop
            if (connection.query(obd.commands.RELATIVE_THROTTLE_POS).value.magnitude == 0.0):   #if OBD throttle pedal is back to zero 
                LIMITCALIBLOW = i-2     #set the lower Limit, where the throttle pedal is zero to servo angle i-2
                break       #exits the endless loop
            time.sleep(0.05)    #waits 0.05 seconds that the system is stationary
    print ("LIMITCALIBLOW: ", LIMITCALIBLOW)

    i = LIMITCALIBLOW
    time.sleep(0.5)     #waits 0.5 seconds that the system is stationary
    while (True):   #same precedure for upper limit vise verser
        moveServo(i)
        i += 1
        if (connection.query(obd.commands.RELATIVE_THROTTLE_POS).value.magnitude > 64.0):
            LIMITCALIBHIGH = i
            break
        time.sleep(0.05)
    print ("LIMITCALIBHIGH: ", LIMITCALIBHIGH)                    

    print("creating lookup table")
    j = LIMITCALIBLOW
    moveServo(j)    #starts creating of the lookup table with the zero throttle position
    time.sleep(0.5) #waits 0.5 seconds that the system is stationary
    for i in range(0, len(lookup)):      
        while (connection.query(obd.commands.RELATIVE_THROTTLE_POS).value.magnitude < i):   #moves servo until the relative throttle position of OBD reached i
            moveServo(j)
            j += 1          #next loop servo one dregee more
            time.sleep(0.1) #waits 0.1 seconds that the system is stationary               
        lookup[i] = j   #throttle position i is related to servo angle j
        print("[", i, lookup[i], "]")
        
    throttle = LIMITCALIBLOW    #retracts the throttle pedal back to 0%
    print("calibration finishes")
    
def readOBD():      #function to read data from OBD device
    global cSPEED, cRPM, cENGINE_LOAD, cCOMMANDED_EQUIV_RATIO, cCOOLANT_TEMP, cTIMING_ADVANCE, cINTAKE_TEMP, cMAF, cRELATIVE_THROTTLE_POS, readallobd, obdfinish
    cSPEED = connection.query(obd.commands.SPEED).value.magnitude   #reads every time function readOBD called the current speed from OBD
    if (readallobd == True):    #reads only if readallobd flag is true
        cRPM = connection.query(obd.commands.RPM).value.magnitude
        cENGINE_LOAD = connection.query(obd.commands.ENGINE_LOAD).value.magnitude
        cCOMMANDED_EQUIV_RATIO = connection.query(obd.commands.COMMANDED_EQUIV_RATIO).value.magnitude
        cCOOLANT_TEMP = connection.query(obd.commands.COOLANT_TEMP).value.magnitude
        cTIMING_ADVANCE = connection.query(obd.commands.TIMING_ADVANCE).value.magnitude
        cINTAKE_TEMP = connection.query(obd.commands.INTAKE_TEMP).value.magnitude
        cMAF = connection.query(obd.commands.MAF).value.magnitude
        cRELATIVE_THROTTLE_POS = connection.query(obd.commands.RELATIVE_THROTTLE_POS).value.magnitude
        obdfinish = True        #reading of obd finished now true 
        readallobd = False      #readallobd flag reset to false

def SendFeedbackData():     #function to send feedback data from OBD to operator
    global timestamp, cSPEED, cRPM, cENGINE_LOAD, cCOMMANDED_EQUIV_RATIO, cCOOLANT_TEMP, cTIMING_ADVANCE, cINTAKE_TEMP, cMAF, cRELATIVE_THROTTLE_POS, readallobd, obdfinish
    readallobd = True   #readallobd flag now true
    while (obdfinish == False):     #waits until obd data have been read
        pass
    obdfinish = False   #reset of obdfinish flag
    tempx = float(round(timevalue*1000))    #preparing the time stamp
    mysample = [tempx, float(cSPEED), float(cRPM), float(round(cENGINE_LOAD)), float(cCOMMANDED_EQUIV_RATIO), float(cCOOLANT_TEMP), float(cTIMING_ADVANCE), float(cINTAKE_TEMP), float(cMAF), float(cRELATIVE_THROTTLE_POS)/65*100]
    outlet.push_sample(mysample)    #sending OBD data to operator
        
def ControlLoop():      #function to control the servo motor
    global I, P, cycletime, pfactor, ifactor
    readOBD()   #getting the most recent speed value from OBD
    
    if (control_mode == 0):     #emergency/reset mode
        moveThrottle(0)         #retracts the throttle to 0%
        I=0.0                   #reset of I value

    if (control_mode == 1):     #control mode to maintain the speed
        print ("Difference: ", (target_speed - cSPEED))
        P = (target_speed - cSPEED) * pfactor   #calculating the proportional part of the control equation
        print ("P: ", P)
                if abs(P) < 55:     #anti wind up
            I += (target_speed - cSPEED) * ifactor * (time.time() - cycletime)  #calculating the integral part of the control equation
        if target_speed == 0.0: #if target speed is zero, reset of the I part
            I = 0.0
        print ("I: ", I)
        moveThrottle(P+I)   #move throttle to P+I = actuating variable
    
    if (control_mode == 2):     #direct throttle mode
        moveThrottle(throttle) 
    
    if (control_mode == 4): #save settings
        pfactor = target_speed
        ifactor = throttle
        print ("new saved P: ", pfactor)
        print ("new saved I: ", ifactor)

    cycletime = time.time()     #store the time after code segment run

def TimerInterrupt():   #function for the timer interrupt
    ControlLoop()   #calls the control loop function
    threading.Timer(CONTROLINTERVAL, TimerInterrupt).start()    #function will call itself after CONTROLINTERVAL seconds
    
def moveThrottle(value):    #function to move the servo by throttle value
    if value > 100:
        value = 100
    if value < 0:
        value = 0
    moveServo(lookup[int(value/101*65)])    #normalising the throttle value, picking the servo angle needed for throttle value, calling function to move the servo
    
def moveServo(angle):   #function to move the servo by angle
    if (angle > SERVOLIMITHIGH):
        angle = SERVOLIMITHIGH
    if (angle < SERVOLIMITLOW):
        angle = SERVOLIMITLOW
    pulsewidth=500+angle*2000/180   #calculating the pulsewidth needed to be transmitted to the servo
    pi.set_servo_pulsewidth(19, pulsewidth) #connection pin 19

#=======================initial function calls=========================#
time.sleep(1)
calibration()   #self calibration after program start
TimerInterrupt()    #starting the timer interrupt
timevalue = 0
tstart = time.time()    #storing the start time
cycletime = time.time()

#=======================mainloop==============================#
while True:    #constantly running loop    
    #pulling (receiving) the newest bit of data
    indata = None   #clears indata
    while True:     #constantly running loop 
        lastindata = indata         #caching of the previous indata
        indata, timestamp = inlet.pull_sample(0)    #pulling the sample with lsl
        if(indata == None):         #if the last pulled sample is empty, most recent sample is stored in cache (lastindata)
            indata = lastindata     #reassigning
            break                   #exits the constantly running loop
    
    if not (indata == None):        #if the was data recieved
        control_mode = indata[0]    #seperating the recieved vector
        target_speed = indata[1]    #seperating the recieved vector
        throttle = indata[2]        #seperating the recieved vector
        print("Received data:")
        print("control_mode: ", control_mode)
        print("target_speed: ", target_speed)
        print("throttle: ", throttle) 
   
    t1 = time.time()        #storing the current system time in t1
    SendFeedbackData()      #calling the function SendFeedbackData
    wait = (FEEDBACK_SAMPLE - (time.time() - t1))   #calculating time to wait
    if (wait > 0):
        time.sleep(wait)
    timevalue = time.time()-tstart  #updating the time passed after program start
