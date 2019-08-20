# MyITOPS-2019
# Abstract

The objective of this project is to develop an actuator to control the vehicle’s throttle pedal on a chassis dynamometer. The actuator will be controlled remotely by software running on a separate device. The application of the device can be used in vehicle testing. The actuator can imitate human foot movement to push the throttle pedal to simulate human driving. The device will be connected to the internet, which enables a test engineer to test and control the car, respectively the speed of the test car at any time and any place around the world if there is a stable and fast internet connection. The user can display and record measured values of the car in real time. In this project we cover detailed explanation on actuator design, electrical assembly, software and results. The device will help the automotive industry and save time and cost for test engineers.

# Instructions
# Hamachi Service
Windows:
Just download hamachi and install it.

Raspberry Pi:
https://medium.com/@KyleARector/logmein-hamachi-on-raspberry-pi-ad2ba3619f3a

# pylsl
Windows:
1. open a cmd window with administrator rights
2. go to your python install folder and in 'scripts' using the cd command
	(probably C:\Users\yourname\AppData\Local\Programs\Python\Python37\Scripts)
3. pip install pylsl

Raspberry Pi:
1. Pylsl-library download using $pip3 install pylsl 
2. find folder /home/pi/.local/python3.5/pylsl 
3. replace entire library with either liblsl_python or liblsl all language python
4. liblsl-bcm2708.so from folder C_C++ rename to liblsl32.so and copy into python3.5
https://github.com/pwnsauce8/ZSWI/wiki/using-pyLSL-module-on-raspbian

# pi gpio
Raspberry Pi:
1. Pylsl-library download using $pip3 install pigpio 
2. sudo systemctl enable pigpiod.service
This makes the pigpio-deamon autostart every time.
It must be running if you want to use pigpio library.

# setting up vnc (remote controle)
If there's no network which the Pi automatically connects to:
1. Connect LAN cable between laptop and Pi
2. Install and start network scanner (e.g. netscan)
3. Click options=>ip adress=>auto detect local IP range
4. Look for IPv4 that is not WLAN, Hamachi, Virtual, Hotspot
5. Remember this (your own) IP (e.g. 169.254.13.193) and close window.
6. At "IPv4 From" enter the first three blocks and a zero (196.254.13.0)
7. At "To" enter the first three blocks and 255 (169.254.13.255)
8. On the right, click start scanning.
9. After maximum 30 seconds you'll find your own IP and another one. That's the Pi
10. (Install and) Open VNC and enter the Pi's IP. It'll ask for name and password.
11. User is "pi" and password is "Hallo1234" right now

# good luck and enjoy
