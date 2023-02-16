
import time
import random
import numpy as np
import sys
import os

usbsim = 0
if not (usbsim): import RPi.GPIO as GPIO


GasBoxpin = 12                     # Pin für Kabel zum Arduino "ready für USB - Datenübernahme" ... logisch: GPIO18
                                   # Pin 12 ist die physikalische Pinordnung und dort ist der logische Pin: GPIO18
if not (usbsim):
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(GasBoxpin, GPIO.OUT)
    GPIO.output(GasBoxpin, GPIO.LOW)  # sofort mal auf Off setzen



lasttime = 0
lasttimezoomim = time.time()


# Nach starten mal 1sec Steuerleitung auf High -> Signal an GasBox, dass Raspberry Steuerung übernehmen will
# Das Poti auf der GasBox muss auf Leerlauf stehen, sonst wird über permantentes GRÜN Leuchten der User daran erinnert.

GPIO.output(GasBoxpin, GPIO.HIGH)
time.sleep(1)
GPIO.output(GasBoxpin, GPIO.LOW)

# 100 x Signal schalten, low->high bewirkt in GaxBox jeweils Gaserhöhung um 1%
# Nötig sind min. 3 Samplingwerte pro Gasstellung für sinnvolle Meßwertaufnahme -> zb 3 Sample/s -> 1sec für einen Step

for i in range(0,100):
    time.sleep(0.5)
    GPIO.output(GasBoxpin, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(GasBoxpin, GPIO.LOW)
