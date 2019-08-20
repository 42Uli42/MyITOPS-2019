#Sternfeuerung 1.0 Beta
#python program to be runned on the operators side
#version 7
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
from tkinter import *
from tkinter import filedialog
import tkinter as tk
from tkinter import ttk
from pylsl import StreamInlet, resolve_stream, StreamInfo, StreamOutlet
import time
import csv

#=======================global variables==============================#
PLUSMINUSINTERVALL = 1      #varibale to set the stepwidth of the + and - Button on the GUI
running = True              #flag for emergency stop or general reset
connected = False           #flag to chef if a connection is established
mode = 0                    #mode variable in GUI, Speed mode = 1, angle mode = 2, replay mode = 3, Seetings = 4
recording = False           #flag if the program should record recieved Data
replay = False              #flag if the program should run the loaded reaply file
replaystarttime = None      #variable to store the time when the start button in replay mode was hit to calculate the remaining replay time
replayarray = []            #array to store values from replay file *.csv
replayrowcount = 0          #varibale to store the current position in the array
outputfile = None           #variable for *.csv file writing, includes also the file name
start_rectime=0.0           #time when recording started to normalise the time values starting at 0seconds, preset to 0.0
outputdirectory = ""        #path where the *.csv file will be stored
pvalue = 7.5                #value to tune the pi controller remotely, p-value, linear part of the pi-equation
ivalue = 0.3                #value to tune the pi controller remotely, i-value, integral part of the pi-equation

#=======================Functions==============================#
def ba_reset():     #emergency stop or general reset
    global running, resettext, recording
    #toggles running flag and labels on GUI
    if running == False:
        running = True
        resettext.set("reset")
    else:
        running = False
        resettext.set("arm")
        if recording == True:   #if recording was true, reset of recording
            outputfile.close()
            recording = False
            start_rectime=0.0
            recordtext.set("Record")
        if connected == True:   #if connected, pushing emergency sample
            outlet.push_sample([0, 0, 0])

def ba_transmit():  #transmitting of entered values
    if ((running == True) & (connected == True)):
        if mode == 1:   #speed mode, checks if entered value is valid
            try:
                float(e_speed.get())
            except ValueError:
                e_speed.delete(0,END)
                e_speed.insert(0,"invalid value")
            else:
                if float(e_speed.get())<0:
                    e_speed.delete(0,END)
                    e_speed.insert(0,"invalid value")
                else:
                    outlet.push_sample([1,float(e_speed.get()),0])      #sending data to raspberry py
                    lasttransmit.set("speed = "+e_speed.get()+" km/h")
                    print("sample pushed")
        if mode == 2:   #angle mode, checks if entered value is valid
            try:
                float(e_throttle.get())
            except ValueError:
                e_throttle.delete(0,END)
                e_throttle.insert(0,"invalid value")
            else:
                if (float(e_throttle.get())>100) | (float(e_throttle.get())<0):
                    e_throttle.delete(0,END)
                    e_throttle.insert(0,"invalid value")
                else:
                    outlet.push_sample([2,0,float(e_throttle.get())])      #sending data to raspberry py
                    lasttransmit.set("throttle = "+e_throttle.get()+" %")
                    print("sample pushed")
        
def ba_plus():  #manipulates the value of the entry field by adding the PLUSMINUSINTERVALL value
    if mode == 1:
        try:
            float(e_speed.get())
        except ValueError:
            e_speed.delete(0, END)
            e_speed.insert(0,0)
        else:
            tmp = e_speed.get()
            e_speed.delete(0, END)
            e_speed.insert(0, int(tmp) + int(e_incrementvalue.get()))  
    if mode == 2:
        try:
            float(e_throttle.get())
        except ValueError:
            e_throttle.delete(0, END)
            e_throttle.insert(0,0)
        else:
            if float(e_throttle.get())> 100-int(e_incrementvalue.get()):
                e_throttle.delete(0,END)
                e_throttle.insert(0,100)
            else:
                tmp = e_throttle.get()
                e_throttle.delete(0, END)
                e_throttle.insert(0, int(tmp) + int(e_incrementvalue.get()))

def ba_minus():  #manipulates the value of the entry field by subtracting the PLUSMINUSINTERVALL value
    if mode == 1:
        try:
            float(e_speed.get())
        except ValueError:
            e_speed.delete(0, END)
            e_speed.insert(0,0)
        else:
            if float(e_speed.get()) >= int(e_incrementvalue.get()):
                tmp = e_speed.get()
                e_speed.delete(0, END)
                e_speed.insert(0, int(tmp) - int(e_incrementvalue.get()))
    if mode == 2:
        try:
            float(e_throttle.get())
        except ValueError:
            e_throttle.delete(0, END)
            e_throttle.insert(0,0)
        else:
            if float(e_throttle.get()) >= int(e_incrementvalue.get()):
                tmp = e_throttle.get()
                e_throttle.delete(0, END)
                e_throttle.insert(0, int(tmp) - int(e_incrementvalue.get()))

def on_tab_selected(event):     #function to recognise which tab is selected by the user
    global mode
    selected_tab=event.widget.select()
    tab_text=event.widget.tab(selected_tab, "text")
    if tab_text == "Speed Mode":
        mode = 1
    if tab_text == "Angle Mode":
        mode = 2
    if tab_text == "Replay Mode":
        mode = 3
    if tab_text == "Settings":
        mode = 4

def createOutputStream():   #creates the output stream, settles the communication parameters and establishes the connection
    global outlet
    #stream name: operator, content-type: operator, number of channels (how many values peer sample): 3, frequency: 100 Hz, Datatype: float32, auto-reconnect identifyer: not configured here
    info = StreamInfo('operator', 'operator', 3, 100, 'float32', '1')
    outlet = StreamOutlet(info)

def searchInputStream():    #search for input streams
    global connected, inlet
    streams = resolve_stream('type', 'backstream')  #second argument is the name of the stream from the raspberry pi
    inlet = StreamInlet(streams[0])
    connected = True
    print("backstream found!")
    check1.set(1)

def ba_replaybrowse():  #opens a browse window to set the replay file path
    global replaydirectory
    replaydirectory = filedialog.askopenfilename(filetypes = (("csv-file","*.csv"),("all files","*.*")))
    if not replaydirectory =="":
        e_replaydirectory.delete(0, END)
        e_replaydirectory.insert(0, replaydirectory)

def ba_replaystartstop():   #button to start or stop the playing the replay file
    global replay, replaystarttime, replayarray
    if not e_replaydirectory.get()=="":     #only starts playing the replay file if there is a path entered
        if replaystartstopvalue.get()=="start": #if button was start as hit
            replaystartstopvalue.set("stop")
            with open(e_replaydirectory.get()) as csvfile:  #opens the *.csv file
                readCSV = csv.reader(csvfile, delimiter=";")    #with specified delimiter ;
                                                                #different delimiter could be chosen if necessary
                for row in readCSV:     #writes the *.csv file to vector
                    replayarray.append(row)
            replaystarttime = time.time()   #stores the current time as the replayfile was started
            replayrowcount = 0  #reset replay row count value
            replay = True   #replay flag now true
        else:       #if button was stop as hit
            replay = False  #replay flag now false
            replayarray = []    #clear replayarray
            replayrowcount = 0  #reset replay row count value
            replaystartstopvalue.set("start")
            outlet.push_sample([2,0,0])     #pushes sample to set the throttle to 0%
            lasttransmit.set("throttle = 0%")

def ba_outputbrowse():  #button to set the outputdirectory for the *.csv file in record mode
    global outputdirectory
    outputdirectory = filedialog.askdirectory()
    if not outputdirectory =="":
        e_outputdirectory.delete(0, END)
        e_outputdirectory.insert(0, outputdirectory)

def ba_connect():   #button connect to establish the connection between operator and raspberry pi
    if connected == False:
        createOutputStream()    #calls function to create output stream
        searchInputStream()     #calls function to finde input stream
        time.sleep(25)
        ba_savesetting()        #transmits the setting for the pi controller
        ba_savesetting()

def ba_record():    #button to start recording of recieved obd data
    global recording, outputfile, start_rectime
    if e_outputdirectory.get()=="":     #if outputdirectory is not specified by the user, *.csv file will be written to sternfeuerung program folder
        e_outputdirectory.insert(0, ".")
    if recording == False:  #if recording is not running
        recording = True    #recording flag, now running
        recordtext.set("Stop rec")
        outputfile = open(time.strftime(e_outputdirectory.get()+"/OBD_rec_%Y%m%d_%H%M%S")+".csv", "w")  #creates and opens a *.csv file where the data will be written
        outputfile.write("Time[s];Speed[km/h];RPM[1/min];Engine Load[%];Lambda;Coolant Temperature;Timing Advance;Intake Temp;Mass Airflow;Relative Throttle Position\n")   #writes the first row of the *.csv file for user infomation in post processing
    else:   #recording is running
        recording = False   #recording flag, now false
        start_rectime=0.0   #reset of start rectime
        outputfile.close()  #closing the *.csv file, if not closed, file will be damaged
        recordtext.set("Record")

def ba_savesetting():   #button settings hit
    global connected
    if connected == True:
        outlet.push_sample([4,float(e_pipvalue.get()),float(e_piivalue.get())]) #pushes a sample with the pi controller settings
    
#=======================creation of window==============================#
window = tk.Tk()
window.title("Sternfeuerung 1.0 Beta")

#=======================GUI Variables==============================#
resettext = StringVar()
resettext.set("reset")
feedbackspeed = StringVar()
feedbackthrottle = StringVar()
recordtext = StringVar()
recordtext.set("record")
lasttransmit = StringVar()
replaystartstopvalue = StringVar()
replaystartstopvalue.set("start")
replaytime = StringVar()
feedbackcoolanttemp = StringVar()
feedbackrpm = StringVar()
check1 = IntVar()
check1.set(0)

#=====================Setting of Window Tabs============================# 
tab_parent=ttk.Notebook(window)

tab1=ttk.Frame(tab_parent)
tab1.grid()
tab2=ttk.Frame(tab_parent)
tab2.grid()
tab3=ttk.Frame(tab_parent)
tab3.grid()
tab4=ttk.Frame(tab_parent)
tab4.grid()

tab_parent.bind("<<NotebookTabChanged>>", on_tab_selected)
tab_parent.add(tab1, text="Speed Mode")
tab_parent.add(tab2, text="Angle Mode")
tab_parent.add(tab3, text="Replay Mode")
tab_parent.add(tab4, text="Settings")

#======================arrangement of GUI objects=========================#
#=========================Tab 1: Speed Mode=============================#
l_speed = tk.Label(tab1, text="Target speed").grid(row = 0, column = 0, sticky='w')
e_speed = tk.Entry(tab1, bd=5, width=40)
e_speed.grid(row = 0, column = 1)
b_transmit = ttk.Button(tab1, text="transmit", command=ba_transmit).grid(row = 0, column = 2)
b_reset = ttk.Button(tab1, textvariable=resettext, command=ba_reset).grid(row=0, column=3)
l_lasttransmit = tk.Label(tab1, text="last transmitted:").grid(row = 1, column = 0, sticky='w')
l_lasttransmitvalue = Label(tab1, textvariable=lasttransmit).grid(row = 1, column = 1, sticky='w')
b_minus = ttk.Button(tab1, text="-", command=ba_minus).grid(row = 1, column = 2)
b_plus = ttk.Button(tab1, text="+", command=ba_plus).grid(row = 1, column = 3)
l_cspeed = tk.Label(tab1, text="Current speed").grid(row = 2, column = 0,  sticky='w')
l_cspeedvalue = Label(tab1, textvariable=feedbackspeed).grid(row = 2, column = 1)
l_cspeedunit = tk.Label(tab1, text="km/h").grid(row = 2, column = 2)
l_cthrottle = tk.Label(tab1, text="Throttle position").grid(row = 3, column = 0)
l_cthrottlevalue = Label(tab1, textvariable=feedbackthrottle).grid(row = 3, column = 1)
l_cthrottleunit = tk.Label(tab1, text="%").grid(row = 3, column = 2)
l_ccoolanttemp = tk.Label(tab1, text="Coolant temp").grid(row = 4, column = 0, sticky='w')
l_ctcoolanttempvalue = Label(tab1, textvariable=feedbackcoolanttemp).grid(row = 4, column = 1)
l_ctcoolanttempunit = tk.Label(tab1, text="°C").grid(row = 4, column = 2)
l_crpm = tk.Label(tab1, text="RPM").grid(row = 5, column = 0, sticky='w')
l_crpmvalue = Label(tab1, textvariable=feedbackrpm).grid(row = 5, column = 1)
l_crpmunit = tk.Label(tab1, text="1/min").grid(row = 5, column = 2)
c_connection = ttk.Checkbutton(tab1, text="Connected",variable=check1).grid(columnspan=2,  row = 6, column = 0, sticky = 'w')
b_connect = ttk.Button(tab1, text="connect", command=ba_connect).grid(row = 6, column = 1, sticky='w')
b_record = ttk.Button(tab1, textvariable=recordtext, command=ba_record).grid(row = 6, column = 3)

#=======================Tab 2: Angle Mode==============================#
l_speed = tk.Label(tab2, text="Throttle value").grid(row = 0, column = 0, sticky='w')
e_throttle = tk.Entry(tab2, bd=5, width=40, )
e_throttle.grid(row = 0, column = 1)
b_transmit = ttk.Button(tab2, text="transmit", command=ba_transmit).grid(row = 0, column = 2)
b_reset = ttk.Button(tab2, textvariable=resettext, command=ba_reset).grid(row=0, column=3)
l_lasttransmit = tk.Label(tab2, text="last transmitted:").grid(row = 1, column = 0, sticky='w')
l_lasttransmitvalue = Label(tab2, textvariable=lasttransmit).grid(row = 1, column = 1, sticky='w')
b_minus = ttk.Button(tab2, text="-", command=ba_minus).grid(row = 1, column = 2)
b_plus = ttk.Button(tab2, text="+", command=ba_plus).grid(row = 1, column = 3)
l_cspeed = tk.Label(tab2, text="Current speed").grid(row = 2, column = 0,  sticky='w')
l_cspeedvalue = Label(tab2, textvariable=feedbackspeed).grid(row = 2, column = 1)
l_cspeedunit = tk.Label(tab2, text="km/h").grid(row = 2, column = 2)
l_cthrottle = tk.Label(tab2, text="Throttle position").grid(row = 3, column = 0)
l_cthrottlevalue = Label(tab2, textvariable=feedbackthrottle).grid(row = 3, column = 1)
l_cthrottleunit = tk.Label(tab2, text="%").grid(row = 3, column = 2)
l_ccoolanttemp = tk.Label(tab2, text="Coolant temp").grid(row = 4, column = 0, sticky='w')
l_ctcoolanttempvalue = Label(tab2, textvariable=feedbackcoolanttemp).grid(row = 4, column = 1)
l_ctcoolanttempunit = tk.Label(tab2, text="°C").grid(row = 4, column = 2)
l_crpm = tk.Label(tab2, text="RPM").grid(row = 5, column = 0, sticky='w')
l_crpmvalue = Label(tab2, textvariable=feedbackrpm).grid(row = 5, column = 1)
l_crpmunit = tk.Label(tab2, text="1/min").grid(row = 5, column = 2)
c_connection = ttk.Checkbutton(tab2, text="Connected",variable=check1).grid(columnspan=2,  row = 6, column = 0, sticky = 'w')
b_connect = ttk.Button(tab2, text="connect", command=ba_connect).grid(row = 6, column = 1, sticky='w')
b_record = ttk.Button(tab2, textvariable=recordtext, command=ba_record).grid(row = 6, column = 3)

#=======================Tab 3: Replay Mode==============================#
l_replaydirectory = tk.Label(tab3, text="Replay directory").grid(row=0, column=0)
e_replaydirectory = tk.Entry(tab3, bd=5, width=40)
e_replaydirectory.grid(row=0, column=1)
b_replaybrowse = ttk.Button(tab3, text="browse", command=ba_replaybrowse).grid(row=0, column=2)
b_replaystartstop = ttk.Button(tab3, textvariable=replaystartstopvalue, command=ba_replaystartstop).grid(row=0, column=3)
l_lasttransmit = tk.Label(tab3, text="last transmitted:").grid(row = 1, column = 0, sticky='w')
l_lasttransmitvalue = Label(tab3, textvariable=lasttransmit).grid(row = 1, column = 1, sticky='w')
l_replayprocentleft = Label(tab3, textvariable=replaytime)
l_replayprocentleft.grid(row = 1, column = 3)
l_cspeed = tk.Label(tab3, text="Current speed").grid(row = 2, column = 0,  sticky='w')
l_cspeedvalue = Label(tab3, textvariable=feedbackspeed).grid(row = 2, column = 1)
l_cspeedunit = tk.Label(tab3, text="km/h").grid(row = 2, column = 2)
l_pthrottle = tk.Label(tab3, text="Throttle position").grid(row = 3, column = 0)
l_pthrottlevalue = Label(tab3, textvariable=feedbackthrottle).grid(row = 3, column = 1)
l_pthrottleunit = tk.Label(tab3, text="%").grid(row = 3, column = 2)
l_ccoolanttemp = tk.Label(tab3, text="Coolant temp").grid(row = 4, column = 0, sticky='w')
l_ctcoolanttempvalue = Label(tab3, textvariable=feedbackcoolanttemp).grid(row = 4, column = 1)
l_ctcoolanttempunit = tk.Label(tab3, text="°C").grid(row = 4, column = 2)
l_crpm = tk.Label(tab3, text="RPM").grid(row = 5, column = 0, sticky='w')
l_crpmvalue = Label(tab3, textvariable=feedbackrpm).grid(row = 5, column = 1)
l_crpmunit = tk.Label(tab3, text="1/min").grid(row = 5, column = 2)
c_connection = ttk.Checkbutton(tab3, text="Connected",variable=check1).grid(columnspan=2,  row = 6, column = 0, sticky = 'w')
b_connect = ttk.Button(tab3, text="connect", command=ba_connect).grid(row = 6, column = 1, sticky='w')
b_record = ttk.Button(tab3, textvariable=recordtext, command=ba_record).grid(row = 6, column = 3)

#=======================Tab 4: Settings==============================#
l_outputdirectory = tk.Label(tab4, text="Output directory").grid(row=0, column=0, sticky='w')
e_outputdirectory = tk.Entry(tab4, bd=5, width=40)
e_outputdirectory.grid(row=0, column=1)
b_outputbrowse = ttk.Button(tab4, text="browse", command=ba_outputbrowse).grid(row=0, column=3)
l_incrementvalue = tk.Label(tab4, text="Increment").grid(row=1, column=0, sticky='w')
e_incrementvalue = tk.Entry(tab4, bd=5, width=8)
e_incrementvalue.grid(row=1, column=1, sticky='w')
l_pip = tk.Label(tab4, text="p value").grid(row=2, column=0, sticky='w')
e_pipvalue = tk.Entry(tab4, bd=5, width=8)
e_pipvalue.grid(row=2, column=1, sticky='w')
l_pii = tk.Label(tab4, text="i value").grid(row=3, column=0, sticky='w')
e_piivalue = tk.Entry(tab4, bd=5, width=8)
e_piivalue.grid(row=3, column=1, sticky='w')
b_savesetting = ttk.Button(tab4, text="Save", command=ba_savesetting).grid(row=3, column=3)

#===================preset of GUI entry fields==========================#
e_incrementvalue.insert(0, 1)
e_speed.insert(0, 0)
e_throttle.insert(0, 0)
e_outputdirectory.insert(0, ".")
e_pipvalue.insert(0,pvalue)
e_piivalue.insert(0,ivalue)

tab_parent.pack(expand=1, fill='both')

#=======================mainloop==============================#
while(True):    #constantly running loop    
    window.update_idletasks()   #tkinter funtion to update the GUI
    window.update()

    if (connected):     #only runs if the GUI (operator side) is connected to the raspberry pi (controler side)
        #pulling (receiving) the newest bit of data if program falls behind in the stream
        indata = None   #clears indata
        while True:     #constantly running loop
            lastindata = indata         #caching of the previous indata
            indata, timestamp = inlet.pull_sample(0)    #pulling the sample with lsl
            if (indata == None):        #if the last pulled sample is empty, most recent sample is stored in cache (lastindata)
                indata = lastindata     #reassigning
                break                   #exits the constantly running loop

        if not (indata == None):    #if the was data recieved
            if (recording) & (start_rectime == 0.0):    #if recording is activated and start_rectime is in initial state
                start_rectime = indata[0]               #start_rectime is set to the timestamp of the first recieved sample
                
            if recording == True:   #if recording is activated, writes normalise Timestamppulles and Data to *.csv file
                outputfile.write(str((indata[0]-start_rectime)/1000)+";"+str(indata[1])+";"+str(indata[2])+";"+str(indata[3])+";"+str(indata[4])+";"+str(indata[5])+";"+str(indata[6])+";"+str(indata[7])+";"+str(indata[8])+";"+str(indata[9])+"\n")

            #refreshes the variables that are shown in the GUI to the most recent value
            feedbackspeed.set(indata[1]) 
            feedbackthrottle.set(indata[9])
            feedbackcoolanttemp.set(indata[5])
            feedbackrpm.set(indata[2])

        if replay == True:  #if replay mode is active and start button was hit
            if len(replayarray)>replayrowcount:     #checks if the end of the replayfile is reached            
                if (time.time() - replaystarttime)> (float(replayarray[replayrowcount][0])):    #checks with time after start and timestamps in replay *.csv file if the time to send the next sample is reached
                    outlet.push_sample([1,float(replayarray[replayrowcount][1]),0])             #pushes the next speed sample
                    lasttransmit.set("replayspeed = "+replayarray[replayrowcount][1]+" km/h")   #refreshes the varibale which is shown in the GUI
                    replayrowcount = replayrowcount + 1                                         #increases the row count for the *.csv file
            else:   #if last value of the replayfile was pushed
                replay = False      #replay is now not longer running
                replayrowcount = 0  #reset of replayrowcount to 0
            
                replaystartstopvalue.set("start")   #replay stop button now start
                outlet.push_sample([1,0,0])         #pushes sample with throttle padle angle 0
                replayarray = []                    #cleares replayarray
            if not replayarray == []:       #if there is data in the replayarray, label on GUI to show elapsed and total time of the replay
                replaytime.set(str(round((time.time() - replaystarttime)*10)/10) + "/" + str(replayarray[len(replayarray)-1][0]) + "s")
        
    time.sleep(0.02)    #short timer to prevent the program from running as fast as possible
                        #results here in 50Hz refresh rate
                        #value can be lowered to save cpu power on slow computers
