import platform
import os
import threading
import serial
import glob
import sys
import RoboClaw_Controller.RoboClaw as RoboClaw

import ADAFruit_CharLCDPlate.IEEEMenu as LCD

#Used for OS Specific Settings
isLinux = False
isDarwin = False
isWindows = False

#RoboClaw Related Variables
serialConnRate = 0.2
serialBaudRate = 115200
RC_SPD1 = 0
RC_SPD2 = 0
RC_ENC1 = 0
RC_ENC2 = 0
RC_TEMP = 0
RC_MBAT = 0
RC_PORT = ""
RC_VER = ""

#LCD Related Variables
displayRefreshRate = 0.2
#displayBacklight = 1
#displayContrast = 1
displayIndicatorIndex = 0;
displayIndicator = "****************************"

#Shared Variables
stillRunning = True
currentTask = ""
active_serial_ports = []
fieldSide = 'S'

#Clear Console Utility Command, compatible with all platforms.
#Used for debug display and general UI.
def clearConsole():
    if isLinux:
        os.system("clear")
    elif isDarwin:
        os.system("Clear")
    elif isWindows:
        os.system("cls")

#Detects Current OS and changes the corresponding boolean.
#Used for localized console commands and serial port detection.
def osDetect():
    global isLinux
    global isDarwin
    global isWindows
    os = platform.system()

    if os == 'Linux' or os == 'Linux2' or os == 'cygwin':
        #LCD Imports only run code is running on the Pi.
        #No LCD on PCs, along with Pi Specific modifications.
        #import ADAFruit_CharLCDPlate.IEEEMenu as LCD
        isLinux = True
    elif os == 'Windows':
        isWindows = True
    elif os == 'Darwin':
        isDarwin = True
    else:
        print "Unsupported Platform (" + os + "), exiting."
        raise EnvironmentError('Unsupported platform')

#Gathers Active Serial Ports on all Platforms.
#Retuns an array of all ports.
def portDetect():
    global active_serial_ports

    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            active_serial_ports.append(port)
        except (OSError, serial.SerialException):
            pass

#Attempt to Connect to the RoboClaw using previously found ports.
def setupRoboClaw():
    global RC_PORT
    global RC_VER
    global currentTask

    #Loop Through all Available Ports and try to Connect to RoboClaw.
    for p in active_serial_ports:
	RC_PORT = p   
	print "Attempting Connection to RoboClaw on " + RC_PORT
        RoboClaw.Open(RC_PORT, serialBaudRate)
	
	version = RoboClaw.ReadVersion()
	if version[0]:
	    RC_VER = version[1]
	    currentTask = "RoboClaw Connected"
            print "Connected to " + RC_VER + "Active Port: " + RC_PORT + "\n"
	    return
	else:
	    print "Failed\n"
    
    currentTask = "Conn. RoboClaw Fail"
    print "Could Not Find RoboClaw Controller on Available Ports. (Is it plugged in / on?)"
    raise SystemExit

#Method to Update the Visual Indicator in Debug Display
def displayIndicatorUpdate():
    global displayIndicator
    global displayIndicatorIndex

    if displayIndicatorIndex == 31:
        displayIndicatorIndex = 0
    else:
        displayIndicatorIndex = displayIndicatorIndex + 1

    displayIndicator = ""

    rStart = 31 - displayIndicatorIndex
    rEnd = 31 - rStart

    for i in range(rStart):
       displayIndicator += "*"

    displayIndicator += "O"

    for i in range(rEnd):
       displayIndicator += "."

def DriveMixSpeedDist(speed, distance):
    global currentTask

    currentTask = "DR S:",speed," D:",distance 
    #SPD1, DST1, SPD2, DST2, buffer 
    RoboClaw.SetMixedSpeedDistance(speed,distance,speed,distance,0)

#Rudimentary Drive for Time Command
def roboclaw_driveTime(motor, speed, time):
    if speed > 0:
        currentTask = "Drive Forward - MTR:", motor," SPD:", speed, " TME:", time
        if motor == 1:
            RoboClaw.M1Forward(speed)
            time.sleep(time)
            RoboClaw.M1Forward(0)
        elif motor == 2:
            RoboClaw.M2Forward(speed)
            time.sleep(time)
            RoboClaw.M2Forward(0)
        elif motor == 3:
            RoboClaw.M1Forward(speed)
            RoboClaw.M2Forward(speed)
            time.sleep(time)
            RoboClaw.M1Backward(0)
            RoboClaw.M2Backward(0)
    elif speed < 0:
        currentTask = "Drive Backward - M:", motor," SPD:", speed, " T:", time
        if motor == 1:
            RoboClaw.M1Backward(speed)
            time.sleep(time)
            RoboClaw.M1Backward(0)
        elif motor == 2:
            RoboClaw.M2Backward(speed)
            time.sleep(time)
            RoboClaw.M2Backward(0)
        elif motor == 3:
            RoboClaw.M1Backward(speed)
            RoboClaw.M2Backward(speed)
            time.sleep(time)
            RoboClaw.M1Forward(0)
            RoboClaw.M2Forward(0)

#Rudimentary Drive for Distance Command.
#Must Determine Relation of Encoder Values to Distance. Avg 3 values may be beneficial.
#
#This method pulls the global encoder variables, meaning it will not work unless
#the threaded get info methods are running and updating the RC_ENCx variables.
def roboclaw_driveDistance(motor, speed, distance):
    if speed > 0:
        currentTask = "Drive Forward - M:", motor," SPD:", speed, "DST:", distance
        if motor == 0:
            ENC1_START = RC_ENC1
            RoboClaw.M1Forward(speed)

            while 1:
                ENC1_CURR = RC_ENC1
                if ENC1_START + ENC1_CURR == distance:
                    RoboClaw.M1Forward(0)
                    ret
        elif motor == 1:
            ENC2_START = RC_ENC2
            RoboClaw.M2Forward(speed)

            while 1:
                ENC2_CURR = RC_ENC2
                if ENC2_START + ENC2_CURR == distance:
                    RoboClaw.M2Forward(0)
                    ret
        elif motor == 2:
            ENC1_START = RC_ENC1
            ENC2_START = RC_ENC2
            RoboClaw.M1Forward(speed)
            RoboClaw.M2Forward(speed)

            while 1:
                ENC1_CURR = RC_ENC1
                ENC2_CURR = RC_ENC2
                if ENC1_START + ENC1_CURR == distance and ENC2_START + ENC2_CURR == distance:
                    RoboClaw.M1Forward(0)
                    RoboClaw.M2Forward(0)
                    ret
    elif speed < 0:
        currentTask = "Drive Backward - M:", motor," SPD:", speed, "DST:", distance
        if motor == 0:
            ENC1_START = RC_ENC1
            RoboClaw.M1Backward(speed)

            while 1:
                ENC1_CURR = RC_ENC1
                if ENC1_START + ENC1_CURR == distance:
                    RoboClaw.M1Backward(0)
                    ret
        elif motor == 1:
            ENC2_START = RC_ENC2
            RoboClaw.M2Backward(speed)

            while 1:
                ENC2_CURR = RC_ENC2
                if ENC2_START + ENC2_CURR == distance:
                    RoboClaw.M2Backward(0)
                    ret
        elif motor == 2:
            ENC1_START = RC_ENC1
            ENC2_START = RC_ENC2
            RoboClaw.M1Backward(speed)
            RoboClaw.M2Backward(speed)

            while 1:
                ENC1_CURR = RC_ENC1
                ENC2_CURR = RC_ENC2
                if ENC1_START + ENC1_CURR == distance and ENC2_START + ENC2_CURR == distance:
                    RoboClaw.M1Backward(0)
                    RoboClaw.M2Backward(0)
                    ret

#Rudimentary Drive for Distance Command.
#Must Determine Relation of Encoder Values to Distance. Avg 3 values may be beneficial.
#
#This method calls for values right from the RoboClaw. Running this while a
#threaded roboclaw get info method will most likely crash immediately.
def roboclaw_driveDistanceStandalone(motor, speed, distance):
    if speed > 0:
        currentTask = "Drive Forward - M:", motor," SPD:", speed, "DST:", distance
        if motor == 0:
            ENC1_START = RoboClaw.ReadM1Encoder()
            RoboClaw.M1Forward(speed)

            while 1:
                time.sleep(serialConnRate)
                ENC1_CURR = RoboClaw.ReadM1Encoder()
                if ENC1_START + ENC1_CURR == distance:
                    RoboClaw.M1Forward(0)
                    ret
        elif motor == 1:
            ENC2_START = RoboClaw.ReadM2Encoder()
            RoboClaw.M2Forward(speed)

            while 1:
                time.sleep(serialConnRate)
                ENC2_CURR = RoboClaw.ReadM2Encoder()
                if ENC2_START + ENC2_CURR == distance:
                    RoboClaw.M2Forward(0)
                    ret
        elif motor == 2:
            ENC1_START = RoboClaw.ReadM1Encoder()
            ENC2_START = RoboClaw.ReadM2Encoder()
            RoboClaw.M1Forward(speed)
            RoboClaw.M2Forward(speed)

            while 1:
                time.sleep(serialConnRate)
                ENC1_CURR = RoboClaw.ReadM1Encoder()
                ENC2_CURR = RoboClaw.ReadM2Encoder()
                if ENC1_START + ENC1_CURR == distance and ENC2_START + ENC2_CURR == distance:
                    RoboClaw.M1Forward(0)
                    RoboClaw.M2Forward(0)
                    ret
    elif speed < 0:
        currentTask = "Drive Backward - M:", motor," SPD:", speed, "DST:", distance
        if motor == 0:
            ENC1_START = RoboClaw.ReadM1Encoder()
            RoboClaw.M1Backward(speed)

            while 1:
                time.sleep(serialConnRate)
                ENC1_CURR = RoboClaw.ReadM1Encoder()
                if ENC1_START + ENC1_CURR == distance:
                    RoboClaw.M1Backward(0)
                    ret
        elif motor == 1:
            ENC2_START = RoboClaw.ReadM2Encoder()
            RoboClaw.M2Backward(speed)

            while 1:
                time.sleep(serialConnRate)
                ENC2_CURR = RoboClaw.ReadM2Encoder()
                if ENC2_START + ENC2_CURR == distance:
                    RoboClaw.M2Backward(0)
                    ret
        elif motor == 2:
            ENC1_START = RoboClaw.ReadM1Encoder()
            ENC2_START = RoboClaw.ReadM2Encoder()
            RoboClaw.M1Backward(speed)
            RoboClaw.M2Backward(speed)

            while 1:
                time.sleep(serialConnRate)
                ENC1_CURR = RoboClaw.ReadM1Encoder()
                ENC2_CURR = RoboClaw.ReadM2Encoder()
                if ENC1_START + ENC1_CURR == distance and ENC2_START + ENC2_CURR == distance:
                    RoboClaw.M1Backward(0)
                    RoboClaw.M2Backward(0)
                    ret

#Threaded GetSpeed Method
#Get Speed and Encoder Data for Both Motors
def thread_roboclaw_getSpeed(threadName, serialLimit):
    global currentTask
    global RC_SPD1
    global RC_SPD2
    global RC_ENC1
    global RC_ENC2

    while 1:
       time.sleep(serialLimit)

       try:
           RC_SPD1 = RoboClaw.ReadM1Speed()
           RC_SPD2 = RoboClaw.ReadM2Speed()
           RC_ENC1 = RoboClaw.ReadM1Encoder()
           RC_ENC2 = RoboClaw.ReadM2Encoder()
       except:
           currentTask = "Failed to Read Speed & Encoders"

#Threaded GetStatus Method
#Same as GetSpeed above, but with more data.
def thread_roboclaw_getStatusExp(threadName, serialLimit):
    global currentTask
    global RC_SPD1
    global RC_SPD2
    global RC_ENC1
    global RC_ENC2
    global RC_TEMP
    global RC_MBAT

    try:

        while 1:
           time.sleep(serialLimit)
    	   RC_TEMP = 0
     	   RC_MBAT = 0

           try:
               RC_SPD1 = RoboClaw.ReadM1Speed()
               RC_SPD2 = RoboClaw.ReadM2Speed()
           except:
               currentTask = "Failed to Read Speed"

           try:
               RC_ENC1 = RoboClaw.ReadM1Encoder()
               RC_ENC2 = RoboClaw.ReadM2Encoder()
           except:
               currentTask = "Failed to Read Encoders"

           temp = RoboClaw.ReadTemperature()
           if temp[0]:
               RC_TEMP = temp[1]/10.0
           #else:
               #currentTask = "Failed to read Tempurature"

           mbat = RoboClaw.ReadMainBattery()
           if mbat[0]:
               RC_MBAT = mbat[1]/10.0
           #else:
               #currentTask = "Failed to Read Main Battery"
    except:
        currentTask = "Connection Error (Get Status)"

#Threaded GetStatus Method
#Same as GetSpeed above, but with more data.
def thread_roboclaw_getStatus(threadName, serialLimit):
    global currentTask
    global RC_SPD1
    global RC_SPD2
    global RC_ENC1
    global RC_ENC2
    global RC_TEMP
    global RC_MBAT
    global RC_LBAT

    while 1:
       time.sleep(serialLimit)

       RC_SPD1 = RoboClaw.ReadM1Speed()
       RC_SPD2 = RoboClaw.ReadM2Speed()
       RC_ENC1 = RoboClaw.ReadM1Encoder()
       RC_ENC2 = RoboClaw.ReadM2Encoder()

       temp = RoboClaw.ReadTemperature()
       if temp[0]:
           RC_TEMP = temp[1]/10.0
       #else:
           #currentTask = "Failed to read Tempurature"

       mbat = RoboClaw.ReadMainBattery()
       if mbat[0]:
           RC_MBAT = mbat[1]/10.0
       #else:
           #currentTask = "Failed to Read Main Battery"

#Not Final
def thread_display_statusUpdate(threadName, refreshRate):
    while 1:
        time.sleep(refreshRate)

        #battery, #field, #undef,  curent task
        screen_vars = [RC_MBAT, fieldSide, "", currentTask]
        LCD.display_menu(screen_vars)

#Not Implemented or Final
def thread_display_interactiveUpdate(threadName, refreshRate, backlight, contrast):
    global currentTask

    time.sleep(1)

    currentTask = "Interactive Display Updated"

#Threaded Debug Display Method
#Shows Various Values from the RoboClaw Controller, and other Processes for Testing.
def thread_display_debugUpdate(threadName, refreshRate):
    while 1:
        time.sleep(refreshRate)

        clearConsole()

        print "=========== RoboClaw ==========="
        print " Speed 1:       ", RC_SPD1
        print " Speed 2:       ", RC_SPD2
        print " Encoder 1:     ", RC_ENC1
        print " Encoder 2:     ", RC_ENC2
        print " Tempurature:   ", RC_TEMP
        print " Main Battery:  ", RC_MBAT
        print displayIndicator
        print ""
        print currentTask
        displayIndicatorUpdate()

#Test Thread Method Implementing a System Clock
import time
threadCycles = 50
def thread_display_getTime(threadName, delay, cycles):
    global currentTask

    count = 0
    while count < cycles:
       time.sleep(delay)
       count += 1
       print threadName + " - " + time.ctime(time.time())

#Class Handling All Threaded Tasks Related to the RoboClaw Controller
class roboclawThreader (threading.Thread):
    def __init__(self, threadID, name, task):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.task = task

    def run(self):
        if self.task == 1:
            taskdesc = "RoboClaw Speed Updater"
            print "Starting " + self.name + " - Task: " + taskdesc
            thread_roboclaw_getSpeed(self.name, serialConnRate)
            print "Exiting " + self.name + " - Task: " + taskdesc

        elif self.task == 2:
            taskdesc = "RoboClaw Status Updater"
            print "Starting " + self.name + " - Task: " + taskdesc
            thread_roboclaw_getStatus(self.name, serialConnRate)
            print "Exiting " + self.name + " - Task: " + taskdesc

#Class Handling All Threaded Tasks Related to the LCD Display
class displayThreader (threading.Thread):
    def __init__(self, threadID, name, task):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.task = task

    def run(self):
        if self.task == 1:
            taskdesc = "Status Display Updater"
            print "Starting " + self.name + " - Task: " + taskdesc
            thread_display_statusUpdate(self.name, displayRefreshRate)
            print "Exiting " + self.name + " - Task: " + taskdesc

        elif self.task == 2:
            taskdesc = "Interactive Display Updater"
            print "Starting " + self.name + " - Task: " + taskdesc
            thread_display_interactiveUpdate(self.name, displayRefreshRate, displayBacklight, displayContrast)
            print "Exiting " + self.name + " - Task: " + taskdesc

        elif self.task == 3:
            taskdesc = "Debug Display"
            print "Starting " + self.name + " - Task: " + taskdesc
            thread_display_debugUpdate(self.name, displayRefreshRate)
            print "Exiting " + self.name + " - Task: " + taskdesc

        elif self.task == 4:
            taskdesc = "A Useless Time Thread"
            print "Starting " + self.name + " - Task: " + taskdesc
            thread_display_getTime(self.name, 1, threadCycles)
            print "Exiting " + self.name + " - Task: " + taskdesc

    def stop(self):
        self._stop.set()

#=======================================================================================
#================== Main Code Begins ===================================================
#=======================================================================================
osDetect()
clearConsole()

speedThread = roboclawThreader(1, "Thread 1", 1)
statusThread = roboclawThreader(2, "Thread 2", 2)
debugDisplayThread = displayThreader(3, "Thread 3", 3)
statusDisplayThread = displayThreader(4, "Thread 4", 1)
uselessThread = displayThreader(5, "Thread 5", 4)

if isLinux:
    statusDisplayThread.start()

print "--------------------------------------------------------------------------------"
print "------------------------------- Loading Director -------------------------------"
print "---------------- Ensure Everything is Plugged In and Powered On ----------------"
print "--------------------------------------------------------------------------------"
print "Detected OS: " + platform.system() + "..."

print "Detecting Available Serial Ports..."
currentTask = "Port Detection..."
portDetect()
currentTask = ""

print active_serial_ports,"\n"
currentTask = "RoboClaw Connect..."
setupRoboClaw()
RoboClaw.ResetEncoders()

print "Debug UI Starting in 3 Seconds..."
time.sleep(3)
debugDisplayThread.start()

currentTask = "Starting motors in 2 seconds..."
time.sleep(1)
currentTask = "Starting motors in 1 second..."
time.sleep(1)
#Max Speed 2300
DriveMixSpeedDist(2300,6000)

statusThread.start()
#speedThread.start()
#selessThread.start()

while 1:
    time.sleep(0.1)

currentTask = "Main Thread has Closed."
     