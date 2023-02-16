from tkinter import *
import math
import time
import serial
import csv
import random
import numpy as np
import sys
import os
# from PIL import Image, ImageTk # am Mac: pip3 install pillow
# ... am Raspberry hab ich die Funktion ImageTK leider nicht :(

user = "sp"
raspvers = "e9a"
arduvers = 0

rasp = 1                        # 1.. Betrieb am Raspberry (Port und Pfad für Configdateien) / 0.. Betrieb am Mac
usbsim = 0                      # 1.. statt Daten von USB zu lesen werden Messwerte simuliert für Tests ohne Arduino
adcdirekt = 0                   # 2.. Temperatur1..8: der digitale Wert des ADC (0...1023) wird angezeigt OHNE Umrechnung auf oC
                                # 1.. detto mit Berücksichtigung von temp_eich ab config_modoc.csv
                                # 0.. Skalierter Wert für oC
prüfstand = 1                   # 1.. Prüfstand / 0.. Makerbeam-Test-Aufbau bei SP
logg = 1                        # 1.. looging von Meldungen
LowSamplingGrenze = 1           # wenn mehr als 10x hintereinander die Samplingrate kleiner ist, dann auomatisch Restart
EH_Schub = 1                    # 1 .. kg, 1000 .. g

if not (usbsim): import RPi.GPIO as GPIO

# Kalibrierugskonstante
drehmoment_kal = 0
schub_kal = 0

if rasp: fontsizefaktor = 0.7
else:    fontsizefaktor = 1.0

MesswertAnzahl = 10             # nötig für History/Array-berechnung
History = 50                   # Anzahl der historisch im Graphen darzustellender Werte

MaxAnzRundinstrumente = 3
MaxAnzWertegruppen = 15
MaxAnzGraphen = 9
MaxAnzVerschiedeneGraphen = 4

arduinoUSBstartpin = 11                     # Pin für Kabel zum Arduino "ready für USB - Datenübernahme" ... logisch: GPIO17
                                            # Pin 11 ist die physikalische Pinordnung und dort ist der logische Pin: GPIO17
if not (usbsim):
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(arduinoUSBstartpin, GPIO.OUT)
    GPIO.output(arduinoUSBstartpin, GPIO.LOW)  # sofort mal auf Off setzen

Glättung = 10

####################################################################################
### Lese Variable aus Configfile config_USER.csv / im Problemfall setze Defaultwerte
####################################################################################

def configLesen():
    global configfilename

    global fb
    global fh
    global fbteil
    global fhteil
    global rand
    global dockh
    global xSchatten
    global ySchatten

    # Defaultwerte
    fb = 1900
    fh = 1000
    fbteil = 40
    fhteil = 50
    rand = 100
    dockh = 100
    xSchatten = 1
    ySchatten = 1

    configfilename = "config_" + user + ".csv"
    if rasp:
        configfilename = "/home/sp/" + configfilename
    if logg: print ("Einlesen: ", configfilename)
    try:
        configfile = csv.reader(open(configfilename, "r"), delimiter=";")
    except FileNotFoundError:
        print ("Configfile: ", configfilename, " nicht gefunden!")
        return
#        root.mainloop()

    confbez= np.array([])
    confval= np.array([])
    ok = True
    for spalte in configfile:
        confbez = np.append(confbez, spalte[0])
        confval = np.append(confval, spalte[1])
    i = 0;
    if (confbez[i] == "fb"): fb = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", configfilename, " : ", confbez[i]); ok = False
    i = 1;
    if (confbez[i] == "fh"): fh = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", configfilename, " : ", confbez[i]); ok = False
    i = 2;
    if (confbez[i] == "fbteil"): fbteil = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", configfilename, " : ", confbez[i]); ok = False
    i = 3;
    if (confbez[i] == "fhteil"): fhteil = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", configfilename, " : ", confbez[i]); ok = False
    i = 4;
    if (confbez[i] == "rand"): rand = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", configfilename, " : ", confbez[i]); ok = False
    i = 5;
    if (confbez[i] == "dockh"): dockh = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", configfilename, " : ", confbez[i]); ok = False
    i = 6;
    if (confbez[i] == "xSchatten"): xSchatten = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", configfilename, " : ", confbez[i]); ok = False
    i = 7;
    if (confbez[i] == "ySchatten"): ySchatten = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", configfilename, " : ", confbez[i]); ok = False
    if ok:
        print(" einlesen Configfile OK")
    else:
        print("Fehlerhalft Daten im ", configfilename, " ...daher Defaultwerte verwendet")

#######################################################
### Schreibe Variable ins Configfile config_USER.csv
#######################################################

def configSchreiben():

    configfilename = "config_" + user + ".csv"
    if rasp:
        configfilename = "/home/sp/" + configfilename

    if logg: print ("Schreiben: ", configfilename)
    try:
        configfile = csv.writer(open(configfilename, "w"), delimiter=";")
    except FileNotFoundError:
        print ("Configfile: ", configfilename, " kann nicht geschrieben werden")
        root.mainloop()

    confdaten = (
    ["fb", fb],
    ["fh", fh],
    ["fbteil", fbteil],
    ["fhteil", fhteil],
    ["rand", rand],
    ["dockh", dockh],
    ["xSchatten", xSchatten],
    ["ySchatten", ySchatten]
    )
    configfile.writerows(confdaten)
    print ("Configfile: ", configfilename, " schreiben OK")

####################################################################################
### Lese Variable aus Configfile modoc_conf.csv / im Problemfall setze Defaultwerte
### Alternativ gibts das makerbeam_conf.csv ... für den Makterbeam-Teststand
####################################################################################

def modoc_configLesen():
    global madoc_configfilename

    global upm_eich1
    global upm_eich2
    global upm_eich3
    global drehmoment_eich1
    global drehmoment_eich2
    global schub_eich1
    global schub_eich2
    global vccspannung_eich1
    global vccspannung_eich2
    global temp_eich

    # Defaultwerte
    upm_eich1 = 3011100
    upm_eich2 = 1150
    upm_eich3 = -69
    if prüfstand: drehmoment_eich1 = 650
    else:         drehmoment_eich1 = -26652
    if prüfstand: drehmoment_eich2 = 13100
    else:         drehmoment_eich2 = -312
    schub_eich1 = 1160
    schub_eich2 = 4932
    vccspannung_eich1 = 61
    vccspannung_eich2 = 0
    temp_eich = np.array([0, 0, 0, 0, 0, 0, 0, 0])


    if prüfstand:   modoc_configfilename = "modoc_conf.csv"
    else:           modoc_configfilename = "makerbeam_conf.csv"
    if rasp:
        modoc_configfilename = "/home/sp/" + modoc_configfilename

    if logg: print ("Einlesen: ", modoc_configfilename)
    try:
        modoc_configfile = csv.reader(open(modoc_configfilename, "r"), delimiter=";")
    except FileNotFoundError:
        print ("Configfile: ", modoc_configfilename, " nicht gefunden!")
        return

    confbez= np.array([])
    confval= np.array([])
    ok = True
    for spalte in modoc_configfile:
        confbez = np.append(confbez, spalte[0])
        confval = np.append(confval, spalte[1])
    i = 0;
    if (confbez[i] == "upm_eich1"): upm_eich1 = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", modoc_configfilename, " : ", confbez[i]); ok = False
    i = 1;
    if (confbez[i] == "upm_eich2"): upm_eich2 = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", modoc_configfilename, " : ", confbez[i]); ok = False
    i = 2;
    if (confbez[i] == "upm_eich3"): upm_eich3 = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", modoc_configfilename, " : ", confbez[i]); ok = False
    i = 3;
    if (confbez[i] == "drehmoment_eich1"): drehmoment_eich1 = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", modoc_configfilename, " : ", confbez[i]); ok = False
    i = 4;
    if (confbez[i] == "drehmoment_eich2"): drehmoment_eich2 = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", modoc_configfilename, " : ", confbez[i]); ok = False
    i = 5;
    if (confbez[i] == "schub_eich1"): schub_eich1 = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", modoc_configfilename, " : ", confbez[i]); ok = False
    i = 6;
    if (confbez[i] == "schub_eich2"): schub_eich2 = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", modoc_configfilename, " : ", confbez[i]); ok = False
    i = 7;
    if (confbez[i] == "vccspannung_eich1"): vccspannung_eich1 = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", modoc_configfilename, " : ", confbez[i]); ok = False
    i = 8;
    if (confbez[i] == "vccspannung_eich2"): vccspannung_eich2 = int(confval[i]); print(end=".")
    else:   print ("Falscher Inhalt in ", modoc_configfilename, " : ", confbez[i]); ok = False
    for y in range (0, 8):
        i = y + 9;
        if (confbez[i] == "temp_eich" + str(y+1)): temp_eich[y] = int(confval[i]); print(end=".")
        else:   print ("Falscher Inhalt in ", modoc_configfilename, " : ", confbez[i]); ok = False
        print (temp_eich)
    if ok:
        print(" einlesen Configfile OK")
    else:
        print("Fehlerhalft Daten im ", modoc_configfilename, " ...daher Defaultwerte verwendet")

####################################################################################
### Schreibe Variable ins Configfile modoc_conf.csv / im Problemfall setze Defaultwerte
### Alternativ gibts das makerbeam_conf.csv ... für den Makterbeam-Teststand
####################################################################################

def modoc_configSchreiben():

    if prüfstand:   modoc_configfilename = "modoc_conf.csv"
    else:           modoc_configfilename = "makerbeam_conf.csv"
    if rasp:
        modoc_configfilename = "/home/sp/" + modoc_configfilename

    if logg: print ("Schreiben: ", modoc_configfilename)
    try:
        modoc_configfile = csv.writer(open(modoc_configfilename, "w"), delimiter=";")
    except FileNotFoundError:
        print ("Configfile: ", modoc_configfilename, " kann nicht geschrieben werden")
        return

    confdaten = (
    ["upm_eich1", upm_eich1],
    ["upm_eich2", upm_eich2],
    ["upm_eich3", upm_eich3],
    ["drehmoment_eich1", drehmoment_eich1],
    ["drehmoment_eich2", drehmoment_eich2],
    ["schub_eich1", schub_eich1],
    ["schub_eich2", schub_eich2],
    ["vccspannung_eich1", vccspannung_eich1],
    ["vccspannung_eich2", vccspannung_eich2],
    ["temp_eich1", temp_eich[0]],
    ["temp_eich2", temp_eich[1]],
    ["temp_eich3", temp_eich[2]],
    ["temp_eich4", temp_eich[3]],
    ["temp_eich5", temp_eich[4]],
    ["temp_eich6", temp_eich[5]],
    ["temp_eich7", temp_eich[6]],
    ["temp_eich8", temp_eich[7]]
    )
    modoc_configfile.writerows(confdaten)
    print ("Configfile: ", modoc_configfilename, " schreiben OK")

#######################################################
### Setze Variablen, die man im GUI noch verändern kann
#######################################################
def GUIReset():
    global dockx1
    global dockx2
    global docky1
    global docky2
    global grx1
    global grx2
    global gry1
    global gry2
    global grh
    global grAchsenFarbe
    global grAchsenDicke
    global grLinienDicke
    global grXsampling
    global wgx1
    global wgx2
    global wgy1
    global wgy2
    global wgwertfont
    global wgwertsize
    global wgwertabstand
    global rundx1
    global rundx2
    global rundy1
    global rundy2
    global Rundinstrumente
    global rx1
    global rx2
    global ry1
    global ry2
    global rxm
    global rym
    global rrad
    global rau
    global rst1
    global rst2
    global rstt
    global rin
    global rzei
    global rzb
    global rad_i
    ###########
    # Begriffe
    ###########
    # Dock .... unterer vertikaler Bereich für Buttons u a Steuerfelder des GUI
    # Rund .... Rundinstrumente - Messwerte sind durch einen Zeiger dargestellt / nur 1 Messswert je Rundinstrument
    # WG ...... Wertegruppen - zeigen Messwerte nummerisch an / mehrere Messwerte untereinander
    # GR ...... Graphische Liniendarstellung auf Achsen / auch mehrere Messwerte in einem Graph möglich

    # fbteil .. Prozentuale Teilung des Bildschirms in der Breite zwischen Graph und Wertegruppen bzw Rundinstrumente
    # fhteil .. Prozentuale Teilung des Bildschirms in der Höhe zwischen Wertegruppen und Rundinstrumente

    ##################################
    # Bildschirmaufteilung generell
    ##################################
    #
    #       fbteil --> #
    ##################################
    #                  # WG1    WG2  #
    # Graph1           # WG3    WG4  #  fhteil
    #                  # WG5    WG6  #  V
    # Graph2           ###############  #
    #                  # Rund1 Rund2 #
    # Graph x          #             #
    #                  # Rund3 Rund4 #
    ##################################
    #             Dock               #
    ##################################

    # Dock:  links oben:   x= rand   y= fh - dockh - rand
    #        rechts unten: x= fb     y= fh


    dockx1= rand
    docky1= fh-dockh-rand
    dockx2= fb-rand
    docky2= fh-rand

    # Graph: links oben:   x= rand               y= rand
    #        rechts unten: x= grx2= 2/3 von fb   y= docky1

    grx1= rand
    gry1= rand
    grx2= fb/100*fbteil
    gry2= docky1-rand
    grh= (gry2-gry1)/MaxAnzVerschiedeneGraphen- rand
    grAchsenFarbe= "grey10"
    grAchsenDicke= 2
    grXsampling= (grx2-grx1)/History
    grLinienDicke= 3

    # Wertegruppen: links oben:   x= grx2    y= rand
    #               rechts unten: x= fb      y= wgy2= 1/3 von (fh minus dock)

    wgx1= grx2+rand
    wgy1= rand
    wgx2= fb-rand
    wgy2= docky1/100*fhteil
    wgwertfont="fixedsys"
#    wgwertsize= int((wgy2-wgy1)/30)
    wgwertsize= int((wgy2-wgy1)/MaxAnzWertegruppen/2.2)
    wgwertabstand= wgwertsize*2

    # Rundinstrumente: links oben:   x= grx2    y= wgy2
    #                  rechts unten: x= fb      y= docky1
    rundx1= grx2+rand
    rundy1= wgy2+rand
    rundx2= fb-rand
    rundy2= docky1-rand

    rx1 = np.array([0, 0, 0])
    rx2 = np.array([0, 0, 0])
    ry1 = np.array([0, 0, 0])
    ry2 = np.array([0, 0, 0])

    rxm  = np.array([0, 0, 0])
    rym  = np.array([0, 0, 0])
    rrad = np.array([0, 0, 0])
    rau  = np.array([0, 0, 0])

    rst1 = np.array([0, 0, 0])
    rst2 = np.array([0, 0, 0])
    rstt = np.array([0, 0, 0])
    rin  = np.array([0, 0, 0])
    rzei = np.array([0, 0, 0])
    rzb  = np.array([0, 0, 0])

    # Diese Radiusberechnung gilt für 3 Rundinstrumente nebeneinander (und nur 1 Reihe)
    # hinsichtlich Breite: verfügbare Breite - innere Ränder (zw 1. und 2., zw 2. und 3.) / 3 Rundinstrumente  ... Radius=Druchmesser/2
    # hinsichtlich Höhe: verfügbare Höhe /2
    # tatsächerlicher Radius ist kleinerer Wert, von der möglichen Größe hinsichtlich Breite und Höhe
    rad_i = min(((rundx2-rundx1)-2*rand)/3/2, (rundy2-rundy1)/2)

    for x in range(0, MaxAnzRundinstrumente):

        rrad = np.array([rad_i, rad_i, rad_i])

        rx1 = np.array([rundx1,           rundx1+rrad[0]*2+rand,    rundx1+rrad[0]*2+rand+rrad[1]*2+rand])
        rx2 = np.array([rx1[0]+rrad[0]*2, rx1[1]+rrad[1]*2,         rx1[2]+rrad[1]*2])
        ry1 = np.array([rundy1,               rundy1,               rundy1])
        ry2 = np.array([rundy1+rx2[0]-rx1[0], rundy1+rx2[1]-rx1[1], rundy1+rx2[2]-rx1[2]])

        rxm = np.array([rx1[0]+(rx2[0]-rx1[0])/2, rx1[1]+(rx2[1]-rx1[1])/2, rx1[2]+(rx2[2]-rx1[2])/2])
        rym = np.array([ry1[0]+(ry2[0]-ry1[0])/2, ry1[1]+(ry2[1]-ry1[1])/2, ry1[2]+(ry2[2]-ry1[2])/2])
        rau = np.array([max(rrad[0]/50,5), max(rrad[1]/50,5), max(rrad[2]/50,5)])

        rst1 = np.array([max(rrad[0]/7,2), max(rrad[1]/7,2), max(rrad[2]/7,2)])
        rst2 = np.array([max(rrad[0]/30,5), max(rrad[1]/30,5), max(rrad[2]/30,5)])
        rstt = np.array([max(rrad[0]/20,12), max(rrad[1]/30,12), max(rrad[2]/40,12)])
        rin = np.array([max(rrad[0]/10,10), max(rrad[1]/10,10), max(rrad[2]/10,10)])
        rzei = np.array([rrad[0]-rst1[0], rrad[1]-rst1[1], rrad[2]-rst1[2]])
        rzb = np.array([max(rzei[0]/20,10), max(rzei[0]/20,10), max(rzei[0]/20,10)])

    if logg: print("Start... fb= ", fb, " fh= ", fh)
    if logg: print("         fbteil= ", fbteil, " fhteil= ", fhteil)
    if logg: print("         dockx1= ", dockx1, " docky1= ", docky1, " dockx2= ", dockx2, " docky2= ", docky2)
    if logg: print("         grx1= ", grx1, " gry1= ", gry1, " grx2= ", grx2, " gry2= ", gry2)
    if logg: print("         wgx1= ", wgx1, " wgy1= ", wgy1, " wgx2= ", wgx2, " wgy2= ", wgy2)
    if logg: print("         rundx1= ", rundx1, " rundy1= ", rundy1, " rundx2= ", rundx2, " rundy2= ", rundy2," rad_i= ", int(rad_i))
    if logg: print("         usbsim= ", usbsim)

    configSchreiben()

#################################################################
### Reset der Anzeige von Rundinstument, Wertegruppen und Graphen
#################################################################
def AnzeigeObjekteReset():

    for i in range (0, MaxAnzRundinstrumente):
        Rundinstrumente[i].deleteRundinstrument()
        Rundinstrumente[i].zeichneRundinstrument()


    for i in range (0, MaxAnzWertegruppen):
        Wertegruppen[i].deleteWertegruppe()
        Wertegruppen[i].zeichneWertegruppe(wgx1, wgy1+wgwertabstand*(i+1))

    global Graphen
    for i in range (1, MaxAnzGraphen+1):
        ix = i
        if i >= 4:
            ix = 4
        Graphen[i].posx1= grx1
        Graphen[i].posx2= grx2
        Graphen[i].posy1= gry1+((gry2-gry1)/MaxAnzVerschiedeneGraphen)*(ix-1)
        Graphen[i].posy2= gry1+((gry2-gry1)/MaxAnzVerschiedeneGraphen)*(ix  )-rand
        Graphen[i].deleteGraph()
        Graphen[i].zeichneGraph()

#    self.Dockfelder()

#########################
### Globaler Programmtext
#########################

Rundinstrumente = np.array([])
Wertegruppen = np.array([])
Graphen = np.array([])

dataRundinstrument = np.array([0,0,0])
dataGraph = np.array([[1, 2, 3, 4, 5, 6, 7, 8, 9, 0], [1, 2, 3, 4, 5, 6, 7, 8, 9, 0], [1, 2, 3, 4, 5, 6, 7, 8, 9, 0], [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]])
Graphenlinie = False

# Reihenfolge hier               1           2             3         4           5          6         7         8         9        10         11        12        13        14        15
# idex für MX[] und data[]       0           1             2         3           4          5         6         7         8         9         10        11        12        13        14
Messwertname=     np.array(["0", "Drehzahl", "Drehmoment", "Schub",  "Leistung", "Gas",     "Temp1",  "Temp2",  "Temp3",  "Temp4",  "Temp5",  "Temp6",  "Temp7",  "Temp8",  "VCC",    "TempCPU"])
Messwerteinheit=  np.array(["0", "U/m",      "Ncm",        "kg",     "W",        "%",       "oC",     "oC",     "oC",     "oC",     "oC",     "oC",     "oC",     "oC",     "V",      "oC"])
Messwertfarbebg=  np.array(["0", "red",      "blue",       "green",  "orange",   "magenta", "orange", "red",    "blue",   "magenta","orange", "red",    "blue",   "magenta","grey50", "green"])
Messwertfarbefg=  np.array(["0", "grey0",    "grey90",     "grey90", "grey0",    "grey0",   "grey0",  "grey0",  "grey0",  "grey0",  "grey0",  "grey0",  "grey0",  "grey0",  "grey0",  "grey0"])
Messwertmin=      np.array([0,   0,          0,            0,        0,          0,         0,        0,        0,        0,        0,        0,        0,        0,        0,        0])
Messwertmax=      np.array([0,   20000,      400,          3000,     3000,       100,       300,      300,      300,      300,      300,      300,      300,      300,      20,       100])
Skalenmax=        np.array([0,   20,         400,          3000,     3000,       100,       300,      300,      300,      300,      300,      300,      300,      300,      20,       100])
SkalenIncLabel=   np.array([0,   10,          10,          6,        7,          16,        16,       16,       16,       16,       16,       16,       16,       16,       16,       16])
SkalenIncStrich=  np.array([0,   21,          43,          34,       15,          8,         8,        8,        8,        8,        8,        8,        8,        8,        8,        8])
if rasp:
    PORT = '/dev/ttyACM0' # fuer Raspberry
else:
#    PORT = '/dev/tty.usbmodem1421' # fuer Mac
    PORT = '/dev/tty.usbmodem1411' # fuer Mac

configLesen()
modoc_configLesen()

root = Tk()
w = Canvas(root, width=fb, height=fh)
w.pack()

wd=math.pi/2
wi=math.pi*0.2

lasttime = 0

GUIReset()      # 1.tes Mal aufrufen, damit alle Variable definiert sind

class c_Graph:

    def __init__(self, Graphindex):
        self.Nr = Graphindex - 1     #Wegen Zugriff auf Arrays
        self.dataGraph = np.array([])
        self.dataLinie = np.array([])
        self.Graphenlinie = False

    def zeichneGraph(self):
        self.dieXAchse = w.create_line(self.posx1, self.posy2, self.posx2, self.posy2, fill= grAchsenFarbe, width= grAchsenDicke)
        self.dieYAchse = w.create_line(self.posx1, self.posy1, self.posx1, self.posy2, fill= grAchsenFarbe, width= grAchsenDicke)

    def deleteGraph(self):
        w.delete(self.dieXAchse)
        w.delete(self.dieYAchse)

    def updateGraph(self, MesswertNr):
        if self.Graphenlinie:
            if self.dataLinie.size > 0:
                for Linie in np.nditer(self.dataLinie):
                    w.delete(int(Linie))
                self.dataLinie = np.array([])

        for i in range (0, int(dataGraph.size/MesswertAnzahl-1)):
            self.Graphenlinie = True
            #print("ITEM", dataGraph.item(i, MesswertNr), i, MesswertNr)
            self.dataLinie = np.append(self.dataLinie, [w.create_line(grx2-(i)*grXsampling, self.posy2-dataGraph.item(i, MesswertNr), grx2-(i+1)*grXsampling, self.posy2-dataGraph.item(i+1, MesswertNr), fill= Messwertfarbebg[MesswertNr], width= grLinienDicke)])

class c_Wertegruppe:

    def __init__(self, Werteindex, Wertetext, Wertebg, Wertefg):
        self.Nr = Werteindex - 1     #Wegen Zugriff auf Arrays

        self.Werteindex = Werteindex
        self.Wertetext = Wertetext
        self.Wertebg = Wertebg
        self.Wertefg = Wertefg

    def zeichneWertegruppe(self, Wertex, Wertey):
        self.EinLabelWert = Label(root, text=self.Wertetext, bg=self.Wertebg, fg=self.Wertefg,font=(wgwertfont, wgwertsize))
        self.EinLabelWert.pack()
        self.EinLabelWert.place(x=Wertex, y=Wertey, anchor="w")

    def deleteWertegruppe(self):
        self.EinLabelWert.destroy()

    def updateWertegruppe(self, WertegruppeWert, WertegruppeEinheit, WertegruppeName):
#        self.EinLabelWert.config(text = str(int(WertegruppeWert)) + " " + WertegruppeEinheit + " (" + WertegruppeName + ")")
        self.EinLabelWert.config(text = str((WertegruppeWert)) + " " + WertegruppeEinheit + " (" + WertegruppeName + ")")


class Rundinstrument:

    def __init__(self, Nummer, LabelText, LabelBG, LabelFG, Einheit, Name):

        self.Nr = Nummer - 1     #Wegen Zugriff auf Arrays
        wd = math.pi/2
        self.Einheit = Einheit
        self.Name = Name
        self.LabelText = LabelText
        self.LabelBG = LabelBG
        self.LabelFG = LabelFG

        self.wi = math.pi*0.2
        self.minimiert = False
        self.zeichneRundinstrument()

    def zeichneRundinstrument(self):

        self.derRoteRahmen = w.create_oval(rx1[self.Nr], ry1[self.Nr], rx2[self.Nr], ry2[self.Nr], fill="red")
        self.dieGraueFläche = w.create_oval(rx1[self.Nr]+rau[self.Nr], ry1[self.Nr]+rau[self.Nr], rx2[self.Nr]-rau[self.Nr], ry2[self.Nr]-rau[self.Nr], fill="grey90")

        self.EinLabelWert = Label(root, text=self.LabelText, bg=self.LabelBG, fg=self.LabelFG, font=("fixedsys", max(int(rrad[self.Nr]/8),10)))
        self.EinLabelWert.pack()
        self.EinLabelWert.place(x=rxm[self.Nr], y=rym[self.Nr]+rrad[self.Nr]*0.4, anchor="c")
        self.EinLabelWert2 = Label(root, text=self.LabelText, bg=self.LabelBG, fg=self.LabelFG, font=("fixedsys", max(int(rrad[self.Nr]/8),10)))
        self.EinLabelWert2.pack()
        self.EinLabelWert2.place(x=rxm[self.Nr], y=rym[self.Nr]-rrad[self.Nr]*0.4, anchor="c")

        self.SkalenLabel = np.array([])
        self.wi = math.pi*0.2
        i = 0;
        labinc = (Skalenmax[self.Nr+1] - Messwertmin[self.Nr+1])/SkalenIncLabel[self.Nr+1]
        while (self.wi <= math.pi*1.9):
            self.SkalenLabel = np.append(self.SkalenLabel, [Label(root, text=self.LabelText, bg="grey90", fg="grey30", font=("fixedsys", max(int(rrad[self.Nr]/12),2)))])
            self.SkalenLabel[i].pack()
            self.SkalenLabel[i].place(x=rxm[self.Nr]+math.cos(self.wi+wd)*(rrad[self.Nr]-rst1[self.Nr]*1.5), y=rym[self.Nr]+math.sin(self.wi+wd)*(rrad[self.Nr]-rst1[self.Nr]*1.5), anchor="c")
            lab = Messwertmin[self.Nr+1] + labinc * i
            self.SkalenLabel[i].config(text = str(int(lab)))
            self.wi = self.wi + math.pi*1.8/(SkalenIncLabel[self.Nr+1]+1)
            i += 1

        self.wi = math.pi*0.2
        self.dieLinien = np.array([])
        while (self.wi <= math.pi*1.9):
            self.dieLinien = np.append(self.dieLinien, [w.create_line(rxm[self.Nr]+math.cos(self.wi+wd)*(rrad[self.Nr]-rst1[self.Nr]*0.7), rym[self.Nr]+math.sin(self.wi+wd)*(rrad[self.Nr]-rst1[self.Nr]*0.7),rxm[self.Nr]+math.cos(self.wi+wd)*(rrad[self.Nr]-rst2[self.Nr]),rym[self.Nr]+math.sin(self.wi+wd)*(rrad[self.Nr]-rst2[self.Nr]), fill="grey30", width=max(int(rrad[self.Nr]/60),2))])
            self.wi = self.wi + math.pi*1.8/(SkalenIncStrich[self.Nr+1]+1)
        self.wi = math.pi*0.2
        while (self.wi <= math.pi*1.9):
            self.dieLinien = np.append(self.dieLinien, [w.create_line(rxm[self.Nr]+math.cos(self.wi+wd)*(rrad[self.Nr]-rst1[self.Nr]*1.5), rym[self.Nr]+math.sin(self.wi+wd)*(rrad[self.Nr]-rst1[self.Nr]*1.5),rxm[self.Nr]+math.cos(self.wi+wd)*(rrad[self.Nr]-rst2[self.Nr]),rym[self.Nr]+math.sin(self.wi+wd)*(rrad[self.Nr]-rst2[self.Nr]), fill="grey30", width=max(int(rrad[self.Nr]/60),2))])
            self.wi = self.wi + math.pi*1.8/(SkalenIncLabel[self.Nr+1]+1)

        self.dasOvalSchatten = w.create_oval(rxm[self.Nr]-rin[self.Nr]+xSchatten, rym[self.Nr]-rin[self.Nr]+ySchatten, rxm[self.Nr]+rin[self.Nr]+xSchatten, rym[self.Nr]+rin[self.Nr]+ySchatten, outline="grey70", fill="grey70")
        self.dasOval =         w.create_oval(rxm[self.Nr]-rin[self.Nr],           rym[self.Nr]-rin[self.Nr],           rxm[self.Nr]+rin[self.Nr],           rym[self.Nr]+rin[self.Nr], fill="red")

        self.derStrichSchatten = w.create_line(rxm[self.Nr]+xSchatten, rym[self.Nr]+ySchatten, rxm[self.Nr]+math.cos(self.wi+wd)*(rzei[self.Nr]-2)+xSchatten, rym[self.Nr]+math.sin(self.wi+wd)*(rzei[self.Nr]-2)+xSchatten, fill="grey70", width=rzb[self.Nr])
        self.derStrich =         w.create_line(rxm[self.Nr],           rym[self.Nr],           rxm[self.Nr]+math.cos(self.wi+wd)*(rzei[self.Nr]-2),           rym[self.Nr]+math.sin(self.wi+wd)*(rzei[self.Nr]-2), fill="red", width=rzb[self.Nr])
        self.EinLabelWert.config(text = str(self.Nr) + " " + self.Einheit)
        self.EinLabelWert2.config(text = self.Name)
        root.update()

        self.dieCheckbox = Checkbutton(root, text="", variable=self.minimiert)
        self.dieCheckbox.pack()
        self.dieCheckbox.place(x=rx1[self.Nr], y=ry1[self.Nr], anchor="c")

    def deleteRundinstrument(self):

        w.delete(self.derRoteRahmen)
        w.delete(self.dieGraueFläche)
        self.EinLabelWert.destroy()
        self.EinLabelWert2.destroy()
        for Linie in np.nditer(self.dieLinien):
            w.delete(int(Linie))
        for i in range(0, self.SkalenLabel.size):
            self.SkalenLabel[i].destroy()
        w.delete(self.dasOvalSchatten)
        w.delete(self.dasOval)
        w.delete(self.derStrichSchatten)
        w.delete(self.derStrich)
        self.dieCheckbox.destroy()

    def updateRundinstrument(self):

        w.delete(self.dasOvalSchatten)
        w.delete(self.dasOval)
        w.delete(self.derStrichSchatten)
        w.delete(self.derStrich)

        self.EinLabelWert.config(text = str(int(dataRundinstrument[self.Nr])) + " " + self.Einheit)
        self.EinLabelWert2.config(text = self.Name)

        self.derStrichSchatten = w.create_line(rxm[self.Nr]+xSchatten, rym[self.Nr]+ySchatten, rxm[self.Nr]+math.cos(self.wi+wd)*(rzei[self.Nr]-2)+xSchatten, rym[self.Nr]+math.sin(self.wi+wd)*(rzei[self.Nr]-2)+xSchatten, fill="grey70", width=rzb[self.Nr])
        self.dasOvalSchatten =   w.create_oval(rxm[self.Nr]-rin[self.Nr]+xSchatten, rym[self.Nr]-rin[self.Nr]+ySchatten, rxm[self.Nr]+rin[self.Nr]+xSchatten, rym[self.Nr]+rin[self.Nr]+ySchatten, outline="grey70", fill="grey70")
        self.derStrich =         w.create_line(rxm[self.Nr],           rym[self.Nr],           rxm[self.Nr]+math.cos(self.wi+wd)*(rzei[self.Nr]-2),           rym[self.Nr]+math.sin(self.wi+wd)*(rzei[self.Nr]-2), fill="red", width=rzb[self.Nr])
        self.dasOval =           w.create_oval(rxm[self.Nr]-rin[self.Nr],           rym[self.Nr]-rin[self.Nr],           rxm[self.Nr]+rin[self.Nr],           rym[self.Nr]+rin[self.Nr], fill="red")

class App:
    def __init__(self, root):

        frame = Frame(root)
        frame.pack()

        w.create_rectangle(0, 0, fb, fh, fill="grey99")
        w.create_rectangle(dockx1, docky1, dockx2, docky2, fill="grey90")

        self.button = Button(frame, text="QUIT", fg="red", command=frame.quit)
        self.button.pack(side=LEFT)

#        self.slogan = Button(frame, text="Start", command=self.LeseUSB)
#        self.slogan.pack(side=LEFT)

        self.slogan = Button(frame, text="Kal", command=self.Kalibrieren)
        self.slogan.pack(side=LEFT)

        self.slogan = Button(frame, text="Restart", command=self.Restart)
        self.slogan.pack(side=LEFT)

        self.slogan = Button(frame, text="Shutdown", command=self.Shutdown)
        self.slogan.pack(side=LEFT)

        self.slogan = Button(frame, text="Benutzer", command=self.UserKeyIn)
        self.slogan.pack(side=LEFT)

        if logg: print("init")
        self.Dockfelder()

        global Rundinstrumente
        for j in range (1, MaxAnzRundinstrumente+1):
            if j == 1: i = 1 # UPM auf 1.tem Rundinstrument
            if j == 2: i = 2 # Drehmoment auf 2.tem Rundinstrument
            # Schub wird nicht dargestellt
            if j == 3: i = 4 # Leistung auf 3.tem Rundinstrument
            i == j

            Rundinstrumente = np.append(Rundinstrumente, [Rundinstrument(j, Messwertname[i], Messwertfarbebg[i], Messwertfarbefg[i], Messwerteinheit[i], Messwertname[i])])

        global Wertegruppen
        for i in range (1, MaxAnzWertegruppen+1):
            Wertegruppen = np.append(Wertegruppen, [c_Wertegruppe(i, Messwertname[i], Messwertfarbebg[i], Messwertfarbefg[i])])
        for i in range (Wertegruppen.size):
            Wertegruppen[i].zeichneWertegruppe(wgx1, wgy1+wgwertabstand*(i+1))

        global Graphen
        for i in range (1, MaxAnzGraphen+2):
            Graphen = np.append(Graphen, [c_Graph(i)])

        for i in range (1, MaxAnzGraphen+1):
            ix = i
            if i >= 4:
                ix = 4
            Graphen[i].posx1= grx1
            Graphen[i].posx2= grx2
            Graphen[i].posy1= gry1+((gry2-gry1)/MaxAnzVerschiedeneGraphen)*(ix-1)
            Graphen[i].posy2= gry1+((gry2-gry1)/MaxAnzVerschiedeneGraphen)*(ix  )-rand
            Graphen[i].zeichneGraph()

#        logoimg = Image.open("Logo.tiff")
#        logofilename = ImageTk.PhotoImage(logoimg)
#        canvas = Canvas(root, width=fb*0.315, height=fh*0.3)
#        canvas.image = logofilename
#        canvas.create_image(0,0,anchor='nw',image=logofilename)
#        canvas.place(x=fb*0.68, y=rand, anchor="nw")


        if usbsim:
            if logg: print("usbsim = 1 -> USB-Port wird nicht geöffnet", PORT)
        else:
            GPIO.output(arduinoUSBstartpin, GPIO.HIGH)  # ready für Daten!

            global ser
            USBwait = True
            while USBwait:
                try:
                    if logg: print("Öffne USB-Port: ", PORT)
                    ser= serial.Serial(PORT)
                    USBwait = False
                except serial.serialutil.SerialException:
                    print ("init: Keine Daten auf USB (serial.serialutil.SerialException:) ... retry in 1 sec")
                    time.sleep(1)

        self.LeseUSB()

#################################################
### Kalibrieren Dremoment und Schub (Durchführen)
#################################################
    def KalibrierenStart(self):

        global wKalTextfeld
        global wKal
        global KalKeyInfont
        global KalKeyInsize
        global wKalh
        global drehmoment_kal
        global schub_kal

        ok = 0
        i = 0
        nok = 1
        messnr = 0
        last1 = data[1]
        last2 = data[2]
        print ("Kal gestartet " + str(last1) + str(last2))
        self.wKalTextfeld = Label(self.wKal, text="Bisherige Kalibrationswerte = " + str(drehmoment_kal) +
                                  " bzw " + str(schub_kal) +
                                  "                                             ",font=(KalKeyInfont, KalKeyInsize), bg="yellow")
        self.wKalTextfeld.place(x=rand*2, y=wKalh/3, anchor="nw")
        root.update()
        time.sleep(2)

#        TastenAktion1.config(text = "Exit")
        root.update()
        while (ok == 0) & (nok < 11): # Nach 10 erfolglosen Versuchen wird abgebrochen
            if not(usbsim): self.LeseUSBline()
            if taste4 == 0: # Exit gedrückt
                nok = 99
                break
            if usbdatenok == 1:
                data[1] = int(data[1] / drehmoment_eich1 - drehmoment_eich2) # Eichung Drehmoment in Ncm
                data[2] = int((data[2] / schub_eich1 - schub_eich2) * EH_Schub)          # EH_Schub = 1 .. Eichung in kg / EH_Schub = 1000 .. Eichung in g
                data[1] = data[1] + drehmoment_kal
                data[2] = data[2] + schub_kal
            messnr += 1
            if messnr == 5: # nach 5 Messungen wieder prüfen
                messnr = 0
                if (data[1] == last1) & (data[2] == last2): i += 1;
                else:                i =  1; nok += 1; last1 = data[1]; last2 = data[2]
                if i == 5: ok = 1

            self.wKalTextfeld = Label(self.wKal, text=str(nok) + ". Versuch.. (" + str(i) + ". Messwert) Drehmoment= "
                                        + str(last1) + " / " + str(data[1]) + "   Schub= "
                                        + str(last2) + " / " + str(data[2]) + "                                   ",
                                        font=(KalKeyInfont, KalKeyInsize), bg="yellow")
            self.wKalTextfeld.place(x=rand*2, y=wKalh/3, anchor="nw")
            root.update()

        drehmoment_kal = drehmoment_kal-last1
        schub_kal = schub_kal-last2
        time.sleep(2)
        if ok == 1:
            self.wKalTextfeld = Label(self.wKal, text="OK, neue Kalibrationswerte = " + str(drehmoment_kal)
                                        + " bzw " + str(schub_kal)
                                        + "                                                                    ",
                                        font=(KalKeyInfont, KalKeyInsize), bg="yellow")
            modoc_configSchreiben()

        else:
            if nok == 99:
                self.wKalTextfeld = Label(self.wKal, text="Kalibration abgebrochen!"
                                        + "                                                                    ",
                                        font=(KalKeyInfont, KalKeyInsize), bg="yellow")
            else:
                self.wKalTextfeld = Label(self.wKal, text="Kalibration fehlgeschlagen"
                                        + "                                                                    ",
                                        font=(KalKeyInfont, KalKeyInsize), bg="yellow")
        self.wKalTextfeld.place(x=rand*2, y=wKalh/3, anchor="nw")
        TastenAktion1.config(text = "")
        TastenAktion4.config(text = "")

        root.update()
        time.sleep(2)
        print ("Kal beendet " + str(last1) + " nach " + str(nok))

        if usbsim: self.wKal.destroy()

####################################
### Kalibrieren Dremoment und Schub (Fenster)
####################################
    def Kalibrieren(self):

        global wKalTextfeld
        global wKal
        global KalKeyInfont
        global KalKeyInsize
        global wKalh

        wKalb = fb/2
        wKalh = fh/6
        KalKeyInfont="fixedsys"
        KalKeyInsize= int(wKalh/8 * fontsizefaktor)
        wKalx1 = (fb-wKalb)/2
        wKaly1 = (fh-wKalh)*0.3
        wKalx2 = wKalx1+wKalb
        wKaly2 = wKaly1+wKalh

        self.wKal = Canvas(root, width=wKalb, height=wKalh)
        self.wKal.place(x=wKalx1, y=wKaly1, anchor="nw")

        self.wKal.create_rectangle(rand, rand, wKalb, wKalh, fill="yellow")

        wKalTextfeld = Label(self.wKal, text="Sensoren für Drehmoment & Schub kalibrieren...",font=(KalKeyInfont, KalKeyInsize), bg="yellow")
        wKalTextfeld.place(x=rand*2, y=wKalh/3, anchor="nw")

        wKalOK = Button(self.wKal, text="Jetzt kalibrieren", command=self.KalibrierenStart)
        wKalOK.place(x=wKalb-rand*5, y=wKalh-rand*5, anchor="se")

        TastenAktion1.config(text = "Jetzt kal.")
        TastenAktion4.config(text = "Exit")
        root.update()

        if not(usbsim):
            self.LeseUSBline()
            self.LeseUSBline()
            while (taste1 == 1) & (taste4 == 1): self.LeseUSBline()

        if taste1 == 0:
            TastenAktion1.config(text = "")
            root.update()
            self.KalibrierenStart()
            self.wKal.destroy()
            return

        if taste4 == 0:
            self.wKalTextfeld = Label(self.wKal, text="Kalibration abgebrochen!                                                                      " ,
                                      font=(KalKeyInfont, KalKeyInsize), bg="yellow")
            self.wKalTextfeld.place(x=rand*2, y=wKalh/3, anchor="nw")
            TastenAktion1.config(text = "")
            TastenAktion4.config(text = "")
            root.update()
            time.sleep(2)
            self.wKal.destroy()

############################
### User Namen eingeben
############################
    def UserKeyInFinished(self):
        global user

        user = self.wUserEingabefeld.get()
        print ("User is: ", user)

        configfilename = "config_" + user + ".csv"
        ok = True
        try:
            configfile = csv.reader(open(configfilename, "r"), delimiter=";")
        except FileNotFoundError:
            print ("Configfile: ", configfilename, " nicht gefunden!")
            ok = False

        self.wUser.destroy()
        if ok:
            configLesen()
            GUIReset()
            AnzeigeObjekteReset()
        else:
            user = "falsch"
            self.UserKeyIn()


############################
### User Namen eingeben
############################
    def UserKeyIn(self):
        global user

        wUserb = fb/4
        wUserh = fh/4
        UserKeyInfont="fixedsys"
        UserKeyInsize= int(wUserh/12 * fontsizefaktor)

        wUserx1 = (fb-wUserb)/2
        wUsery1 = (fh-wUserh)/2
        wUserx2 = wUserx1+wUserb
        wUsery2 = wUsery1+wUserh

        self.wUser = Canvas(root, width=wUserb, height=wUserh)
        self.wUser.place(x=wUserx1, y=wUsery1, anchor="nw")

        self.wUser.create_rectangle(rand, rand, wUserb, wUserh, fill="grey90")

        wUserTextfeld = Label(self.wUser, text="Benutzer",font=(UserKeyInfont, UserKeyInsize))
        wUserTextfeld.place(x=rand*2, y=wUserh/3, anchor="nw")

        self.wUserEingabefeld = Entry(self.wUser, font=UserKeyInfont, width=5)
        self.wUserEingabefeld.place(x=120, y=wUserh/3, anchor="nw")
        self.wUserEingabefeld.focus()
        if user == "falsch":
            wUserFehlerfeld = Label(self.wUser, text="Kein Config-File für diesen Benutzer!",font=(UserKeyInfont, UserKeyInsize), fg="red")
            wUserFehlerfeld.place(x=rand*2, y=wUserh/3*2, anchor="nw")


        wUserOK = Button(self.wUser, text="OK", command=self.UserKeyInFinished)
        wUserOK.place(x=wUserb-rand*5, y=wUserh-rand*5, anchor="se")
#        root.bind('<Return>', self.UserKeyInFinished)

############################
### Dockfelder zeichnen
############################
    def Dockfelder(self):
        global DockWert11
        global DockWert12
        global DockWert13
        global DockWert14
        global DockWert15
        global TastenWert1
        global TastenWert2
        global TastenWert3
        global TastenWert4
        global TastenAktion1
        global TastenAktion2
        global TastenAktion3
        global TastenAktion4
        global wEingabefbteil
        global wEingabefhteil
        global wEingabeglättung

        dockfont="fixedsys"
        docksize= int(dockh/3*fontsizefaktor)

        DockWert11 = Label(root, text="Sampling", bg="grey90", fg="grey0",font=(dockfont, docksize))
        DockWert11.pack()
        DockWert11.place(x=dockx1+rand+docksize*11.5, y=docky1+dockh*0.5, anchor="e")

        DockWert12 = Label(root, text="Start", bg="grey90", fg="grey0",font=(dockfont, docksize))
        DockWert12.pack()
        DockWert12.place(x=dockx2-rand, y=docky1+dockh*0.5, anchor="e")

        DockWert13 = Label(root, bg="grey90", fg="grey0",font=(dockfont, docksize))
        DockWert13.pack()
        DockWert13.place(x=dockx2-rand-300, y=docky1+dockh*0.5, anchor="e")

        DockWert14 = Label(root, bg="grey90", fg="red",font=(dockfont, int(docksize/2)))
        DockWert14.pack()
        DockWert14.place(x=dockx2-rand-500, y=docky1+dockh*0.5, anchor="e")

        DockWert15 = Label(root, bg="grey90", fg="red",font=(dockfont, int(docksize/2)))
        DockWert15.pack()
        DockWert15.place(x=dockx2-rand-700, y=docky1+dockh*0.5, anchor="e")

        TastenWert1 = Label(root, bg="blue", fg="grey99",font=(dockfont, int(docksize)))
        TastenWert1.pack()
        TastenWert1.place(x=(dockx2-dockx1)/2-90, y=docky1+dockh*0.3, anchor="c")

        TastenWert2 = Label(root, bg="blue", fg="grey99",font=(dockfont, int(docksize)))
        TastenWert2.pack()
        TastenWert2.place(x=(dockx2-dockx1)/2-30, y=docky1+dockh*0.3, anchor="c")

        TastenWert3 = Label(root, bg="blue", fg="grey99",font=(dockfont, int(docksize)))
        TastenWert3.pack()
        TastenWert3.place(x=(dockx2-dockx1)/2+30, y=docky1+dockh*0.3, anchor="c")

        TastenWert4 = Label(root, bg="blue", fg="grey99",font=(dockfont, int(docksize)))
        TastenWert4.pack()
        TastenWert4.place(x=(dockx2-dockx1)/2+90, y=docky1+dockh*0.3, anchor="c")

        TastenAktion1 = Label(root, bg="grey90", fg="blue",font=(dockfont, int(docksize*0.75)))
        TastenAktion1.pack()
        TastenAktion1.place(x=(dockx2-dockx1)/2-90, y=docky1+dockh*0.7, anchor="c")

        TastenAktion2 = Label(root, bg="grey90", fg="blue",font=(dockfont, int(docksize*0.75)))
        TastenAktion2.pack()
        TastenAktion2.place(x=(dockx2-dockx1)/2-30, y=docky1+dockh*0.7, anchor="c")

        TastenAktion3 = Label(root, bg="grey90", fg="blue",font=(dockfont, int(docksize*0.75)))
        TastenAktion3.pack()
        TastenAktion3.place(x=(dockx2-dockx1)/2+30, y=docky1+dockh*0.7, anchor="c")

        TastenAktion4 = Label(root, bg="grey90", fg="blue",font=(dockfont, int(docksize*0.75)))
        TastenAktion4.pack()
        TastenAktion4.place(x=(dockx2-dockx1)/2+90, y=docky1+dockh*0.7, anchor="c")


        wEingabefbteilBreite = 200
        wEingabefbteil = Scale(root, from_= 10, to= 90, length=400, orient = HORIZONTAL, label = "Hor.Teilung", bg="grey90")
        wEingabefbteil.set(fbteil)
        wEingabefbteil.place(x=dockx1+rand+docksize*11.5+rand*4, y=docky1+rand, width=wEingabefbteilBreite, height=dockh-rand*2)

        wEingabefhteilBreite = 100
        wEingabefhteil = Scale(root, from_= 30, to= 70, length=50, orient = VERTICAL, label = "Vert.Tlg.", bg="grey90")
        wEingabefhteil.set(fhteil)
        wEingabefhteil.place(x=dockx1+rand+docksize*11.5+rand*4+wEingabefbteilBreite+rand*4, y=docky1+rand, width=wEingabefhteilBreite, height=dockh-rand*2)

        wEingabeglättungBreite = 80
        wEingabeglättung = Scale(root, from_= 0, to= 20, length=50, orient = VERTICAL, label = "Glätt.", bg="grey90")
        wEingabeglättung.set(Glättung)
        wEingabeglättung.place(x=dockx1+rand+docksize*11.5+rand*4+wEingabefbteilBreite+rand*4+wEingabefhteilBreite+rand*4, y=docky1+rand, width=wEingabeglättungBreite, height=dockh-rand*2)

###############################################
### Restarte das gesamte Programm
###############################################
    def Restart(self):
        i = 1
        os.execv(sys.executable, ['python3.6'] + sys.argv)

###############################################
### Shutdown des Raspberry
###############################################
    def Shutdown(self):
        i = 1
        command = "/usr/bin/sudo /sbin/shutdown now"
        import subprocess
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output = process.communicate()[0]
        print (output)


###############################################
### Zeige Alarmmeldung an
###############################################
    def Alarmanzeige(self, alarmtext):
        alarmfont="courier"
        alarmsize= int(fh/15)

        Alarm1 = Label(root, text=alarmtext, bg="grey10", fg="red",font=(alarmfont, alarmsize))
        Alarm1.pack()
        Alarm1.place(x=fb/2, y=fh/2, anchor="center")

###############################################
### Lese eine Datenzeile von USB ein
###############################################
    def LeseUSBline(self):

        global usbdatenok
        global data

        try:
                    line = ser.readline().decode()
                    datastr = line.split(';')
#                    if logg: print(line)
                    if logg: print(datastr)

# Version e8 ... der letzte MX-Wert: MX40 (Notaus), dazu kommt noch MX41="End"
#   if len(datastr) != 43:
#   if datastr[41] != 'End': usbdatenok = 0
#   for i in range (0, 41):

# Version e9 ... der letzte MX-Wert: MX45 (temp8), dazu kommt noch MX46="End"
#   if len(datastr) != 48:
#   if datastr[46] != 'End': usbdatenok = 0
#   for i in range (0, 46):

                    data = np.array([])
                    print("Länge: ", len(datastr))
                    for i in range (0, len(datastr)-1):
                        if datastr[i] == '': usbdatenok = 0
                    if len(datastr) != 48:
                        usbdatenok = 0
                    else:
                        if datastr[46] != 'End': usbdatenok = 0
                    print(" usbdatenok: ", usbdatenok)
                    if usbdatenok == 1:
                        for i in range (0, 46):
                            if datastr[i] == '': datastr[i]= '0'
                            data = np.append(data, int(datastr[i]))
                            if data[i] < 0: data[i]= data[i]*(-1)

        except serial.serialutil.SerialException:
                    usbdatenok = 0
                    print("LeseUSB: Problem mit SerialException ... retry in 1 sec")
#                    ser= serial.Serial(PORT)
                    time.sleep(1)
        except:
                    usbdatenok = 0
                    print("Ein anderer Fehler bei LeseUSB")
 #                   ser=serial.Serial(PORT)

###############################################
### Lese eine Datenzeile von USB ein
###############################################
    def Tempmap(self,kanal,dig):

        if adcdirekt == 0:
            dig = dig + temp_eich[kanal-1]
#           für 4.100 Ohm Widerstand gegen 5V
#           e = 0.0000026066122037748
#           e = e * dig + 0.0002554650952481
#           e = e * dig + 1.0379113982268
#           e = e * dig - 227.86262468827

#           für 3.300 Ohm Widerstand gegen 5V
            e = -0.000000030341718228761
            e = e * dig + 0.00004414150236422
            e = e * dig - 0.021031159559467
            e = e * dig + 5.4402809972152
            e = e * dig - 597.266702272524
            e= int(e*10)/10

        if adcdirekt == 1:
            e = dig + temp_eich[kanal-1]    # Direkt für Tests und Eichung den ADC Wert (0..1023) anzeigen ABER auch mit Berücksichtigung von temp_eich (aus config_modoc.csv)
        if adcdirekt == 2:
            e = dig         # Direkt für Tests und Eichung den ADC Wert (0..1023) anzeigen

        return e

###############################################
### Lese USB ein und stelle alle Datenwerte dar
###############################################
    def LeseUSB(self):
        global wi
        global wi1
        global di1
        global wi2
        global LabelWert11
        global DockWert11
        global DockWert12
        global werti
        global dataGraph
        global LowSamplingGrenze
        global wEingabefbteil
        global wEingabefhteil
        global wEingabeglättung
        global lastfbteil
        global lastfhteil
        global lastglättung
        global fbteil
        global fhteil
        global data
        global usbdatenok
        global EH_Schub
        global taste1
        global taste2
        global taste3
        global taste4
        global Glättung
        global arduvers


        sim0= 10
        sim1= 600
        First= True
        ErsterMesswert= True
        Startup= False
        LowSampling= 0
        lastfbteil= wEingabefbteil.get()
        lastfhteil= wEingabefhteil.get()
        lastglättung= wEingabeglättung.get()

        RingbuffDrehmoment = np.array([])
        RingbuffDrehmomentMaxTiefe = 100
        RingbuffDrehmomentletzter = 0
        for i in range (0, RingbuffDrehmomentMaxTiefe):
            RingbuffDrehmoment = np.append (RingbuffDrehmoment, [0])

        # 2dimensionaler Buffer: 1te Dimension ist der Index für den Meßwert (0=Drehzahl, 1=Drehmoment), 2te der Ringbuffer selbst
        RingbuffMaxTiefe = 100
        m = 10 # mal für Meßwerte 0..
        Ringbuff = [[0 for x in range(RingbuffMaxTiefe)] for y in range(m)]
        Ringbuffletzter = [0 for x in range(m)]
        Ringbuffältester = [0 for x in range(m)]
        Ringbuffglätttiefe  = [0 for x in range(m)]

#        datag = np.array([])
        datag  = [0 for x in range(45)]

        while True:
            global lasttime
            global dataRundinstrument

            DockWert13.config(text = "Benutzer: " + user)

            if prüfstand: DockWert14.config(text = "")
            else:         DockWert14.config(text = "MakerBeam-Eichung!")

#            DockWert15.config(text = "Gl: " + str(Glättung))

            TastenWert1.config(text = " 1 ")
            TastenWert2.config(text = " 2 ")
            TastenWert3.config(text = " 3 ")
            TastenWert4.config(text = " 4 ")

            TastenAktion1.config(text = "Kalibr.")
            TastenAktion2.config(text = "EH_Sch.")
            TastenAktion3.config(text = " Glätt.")

            fbteil= wEingabefbteil.get()
            if fbteil != lastfbteil:
                lastfbteil = fbteil
                GUIReset()
                AnzeigeObjekteReset()

            fhteil= wEingabefhteil.get()
            if fhteil != lastfhteil:
                lastfhteil = fhteil
                GUIReset()
                AnzeigeObjekteReset()

            Glättung= wEingabeglättung.get()
            if Glättung != lastglättung:
                lastglättung = Glättung
                GUIReset()
                AnzeigeObjekteReset()

            if First:
                First = False
                DockWert12.config(text = "Start: " + time.strftime("%H:%M:%S", time.localtime(time.time())) + " " + str(arduvers) + " " + raspvers)

            sample = float(time.time() - lasttime)
            if (sample > 0.01) :
                DockWert11.config(text = '{:1.1f}'.format(1/sample) + " Sample/sec")

                if int(1/sample) > 10:
                    Startup= True
                if Startup & (int(1/sample) < LowSamplingGrenze):
                    LowSampling += 1
                if Startup & (LowSampling>0) & (int(1/sample >= LowSamplingGrenze)):
                    LowSampling = 0
                if Startup & (LowSampling > 10):
                    for i in range (0, 6):
                        self.Alarmanzeige(" Sample low - Restart in " + str(5-i) + " sec!")
                        root.update()
                        time.sleep(0.5)
                        self.Alarmanzeige("                                ")
                        root.update()
                        time.sleep(0.5)
                    self.Restart()
            lasttime = time.time()

            usbdatenok = 1
            if usbsim:
                sim1 = sim1 + random.randint(-150,150)
                if sim1 < 10:
                    sim1 = 800
                if sim1 > 1100:
                    sim1 = 300
                i = random.randint(0,200)
                sim= np.array([4200-(sim0*4+i*9),    # 0
                8000000-(sim0+i)*5000,               # 1
                sim1,
                random.randint(0,20),
                random.randint(1,10),
                random.randint(10,50),
                random.randint(40,90),
                random.randint(100,130),
                random.randint(120,150),
                random.randint(258,268),    #  9     das sind ADC Werte für 30oC bis  43oC
                random.randint(235,463),    # 10     das sind ADC Werte für 30oC bis  43oC
                random.randint(235,463),    # 11     das sind ADC Werte für  0oC bis 400oC
                random.randint(235,463),    # 12     das sind ADC Werte für  0oC bis 400oC
                0,0,0,0,0,0,0,              # 13..19
                0,0,0,0,0,0,0,0,0,0,        # 20..29
                0,0,0,0,0,1,1,1,1,1,        # 30..39
                0,0,0,0,0,0])               # 40..45
                data = sim
                if sim0<200:
                    sim0 += 5
                else:
                    sim0 += 10
                if sim0 > 1000: sim0= 100
#                time.sleep (0.01)
            else:
                self.LeseUSBline()


            if usbdatenok == 1:
                taste1 = data[36]
                taste2 = data[37]
                taste3 = data[38]
                taste4 = data[39]

                ##################################################
                # Meßwerte eichen oder erst im Raspberry bestimmen
                ##################################################

                # Eichung UPM, Drehmoment, Schub
                if (data[0] > 0): data[0] = int((upm_eich1 + (upm_eich2 - data[0]) * upm_eich3) / data[0])         # Eichung UPM in 1/min
                data[1] = int(data[1] / drehmoment_eich1 - drehmoment_eich2) # Eichung Drehmoment in Ncm
                data[2] = int((data[2] / schub_eich1 - schub_eich2) * EH_Schub)          # EH_Schub = 1 .. Eichung in kg / EH_Schub = 1000 .. Eichung in g
                data[1] = data[1] + drehmoment_kal
                data[2] = data[2] + schub_kal
                if usbsim:          # beim Simulieren zum Testen der Glättung als Drehmoment die GLEICHE Wertekurve wie bei Drehzahl MaxAnzVerschiedeneGraphen
                                    # damit sieht man bei Drehzahl die originalen Werte (ungeglättet) und bei Drehmoment kann man die Glättung testen
                    data[1] = data[0] / Messwertmax[1] * Messwertmax[2]

                datag = data  # data ... Werte vom Arduino      /       datag ... geglättete und auf Messwertname umgespeichte Werte
                              # Weiterverwendet für Rundinstrument, Graphen und Wertedarstellung werden nur die werte aus datag !!!!

#  index für MX[] und data[]       0           1             2         3           4          5         6         7         8         9         10        11        12        13        14
# Messwertname=     np.array(["0", "Drehzahl", "Drehmoment", "Schub",  "Leistung", "Gas",     "Temp1",  "Temp2",  "Temp3",  "Temp4",  "Temp5",  "Temp6",  "Temp7",  "Temp8",  "VCC",    "TempCPU"])

                # Glätten Allgemein
                for m in range (0, 3):  # für Drehzahl (0), Drehmoment (1) und Schub (2)
                    Ringbuffletzter[m] += 1                                  # Nächster Wert kommt in die nächste Ringbufferzelle
                    if Ringbuffletzter[m] >= RingbuffMaxTiefe: Ringbuffletzter[m] = 0
                    Ringbuff[m][Ringbuffletzter[m]] = int(data[m])
                    Ringbuffältester[m] = min(Ringbuffletzter[m] + 1, RingbuffMaxTiefe)   # der älteste Wert ist in der Zelle die das NÄCHSTEMAL überschrieben wird
#                    Ringbuffglätttiefe[m] = 30
                    Ringbuffglätttiefe[m] = Glättung+1      # 0 wäre ev problematischer Wert
                    i = 0
                    datag[m] = 0
                    while (i < Ringbuffglätttiefe[m]):
                        i1 = Ringbuffletzter[m] - i
                        if i1 < 0: i1 = i1 + RingbuffMaxTiefe
                        datag[m] += Ringbuff[m][i1]
                        j = 0
                        if datag[m] > 0: j = int((abs(datag[m] - Ringbuff[m][i1]) * 100 / datag[m]))
                        if (j > 97):    # Der gelesene Wert weicht mehr als x% vom Mittelwert ab
                            break
                        i += 1
                    datag[m] = datag[m] / i
#                    if logg: print ("Glätttiefe für " + str(m) + " ... " + str (i))
#                print (Ringbuff)
#                print (RingbuffDrehmoment)
#                print ("letzter: " + str(RingbuffDrehmomentletzter) + "  ältester: " + str(RingbuffDrehmomentältester) + " Glätttiefe: " + str (i) + " Glätt: " + str (GlättDrehmoment))

                # Bestimmung Leistung: P = 2 x Pi x M x n (P: W, M: Nm, n:1/s)
                datag[3] = int(2 * math.pi * datag[1]/100 * datag[0]/60) # Leistung

                datag[4] = 0   #    vorläufig auf 0 setzen: Gas

                #    umspeichern Temp1..4
                datag[ 5] = self.Tempmap(1,data[ 9])
                datag[ 6] = self.Tempmap(2,data[10])
                datag[ 7] = self.Tempmap(3,data[11])
                datag[ 8] = self.Tempmap(4,data[12])

                #    umspeichern Temp5..8
                datag[ 9] = self.Tempmap(5,data[42])
                datag[10] = self.Tempmap(6,data[43])
                datag[11] = self.Tempmap(7,data[44])
                datag[12] = self.Tempmap(8,data[45])

                # VCC Spannung
                datag[13] = int(10 * data[27] / vccspannung_eich1 - vccspannung_eich2)/10 # Eichung VCC Spannung in V

                # Bestimmung CPU Temperatur
                if rasp:
                    tempFile = open ("/sys/class/thermal/thermal_zone0/temp")
                    cpu_temp = tempFile.read()
                    tempFile.close()
                    data[28] = int(float(cpu_temp)/1000)  # TempCPU
                else: datag[14]= 99
                datag[14] = data[28]                   # vorläufig, da dzt noch nicht konfigurierbar, welche Messwerte angezeigt werden sollen und max 9

                arduvers = data[41]

                #########################################
                # Besonderde Zustände behandeln: Shutdown
                #########################################

                ErsterMesswert = False # für Tests wird das Default-Kalibrieren ausgeschaltet!

                if (taste1 == 0) | ErsterMesswert:  #  Taste 1 gedrückt oder Programmstart
                    ErsterMesswert = False
                    print("Taste 1 gedrückt! -> Kalibrieren")
                    self.Kalibrieren()

                if taste2 == 0:                     # EH_Schub toggeln
                    if EH_Schub == 1:
                        EH_Schub = 1000
                        Messwerteinheit[3] = "g"
                        Messwertmax[3] = 20000
                    else:
                        EH_Schub = 1
                        Messwerteinheit[3] = "kg"
                        Messwertmax[3] = 20
                    print("EH_Schub geändert auf: "+ str(EH_Schub))

                if taste3 == 0:                     # Glättung  toggeln
                    Glättung = Glättung -5
                    if Glättung < 0: Glättung = 20
                    wEingabeglättung.set(Glättung)
                    GUIReset()
                    AnzeigeObjekteReset()

                if data[35] == 0:  #  Shutdown ausgelöst...
                    for i in range (0, 6):
                        self.Alarmanzeige(" Shutdown in... " + str(5-i) + " sec!")
                        root.update()
                        time.sleep(0.5)
                        self.Alarmanzeige("                                ")
                        root.update()
                        time.sleep(0.5)
                    root.update()
                    print("Shutdown Button gedrückt!")
                    self.Shutdown()

                dataRundinstrument = np.array([])
                for j in range(0, Rundinstrumente.size):
                    if j == 0:
                        i = 0 # UPM auf 1.tem Rundinstrument
                        Rundinstrumente[j].wi=float(int(datag[i]) / Messwertmax[i+1] * math.pi*1.6 + math.pi*0.2)
                        dataRundinstrument = np.append(dataRundinstrument, [datag[i]])
                        Rundinstrumente[j].updateRundinstrument()
                    if j == 1:
                        i = 1 # Drehmoment auf 2.tem Rundinstrument
                              # Schub wird nicht dargestellt
                        Rundinstrumente[j].wi=float(int(datag[i]) / Messwertmax[i+1] * math.pi*1.6 + math.pi*0.2)
                        dataRundinstrument = np.append(dataRundinstrument, [datag[i]])
                        Rundinstrumente[j].updateRundinstrument()
                    if j == 2:
                        i = 3 # Leistung auf 3.tem Rundinstrument
                        Rundinstrumente[j].wi=float(int(datag[i]) / Messwertmax[i+1] * math.pi*1.6 + math.pi*0.2)
                        dataRundinstrument = np.append(dataRundinstrument, [datag[i]])
                        Rundinstrumente[j].updateRundinstrument()


                    for i in range (Wertegruppen.size):
#                    Wertegruppen[i].updateWertegruppe(float(int(data[i])+0)/1, Messwerteinheit[i+1], Messwertname[i+1])
                        if i <= 2:
                            Wertegruppen[i].updateWertegruppe(int(datag[i]), Messwerteinheit[i+1], Messwertname[i+1])
                        else:
                            Wertegruppen[i].updateWertegruppe(datag[i], Messwerteinheit[i+1], Messwertname[i+1])

                if dataGraph.size >= History * MesswertAnzahl:
                    dataGraph = np.delete(dataGraph, ([0]), axis=0)   # lösche ältersten Messwert
                dataGraph = np.concatenate((dataGraph, np.array([[0,
                                                                  max(0, min(datag[0]/Messwertmax[1]*grh, grh)),
                                                                  max(0, min(datag[1]/Messwertmax[2]*grh, grh)),
                                                                  max(0, min(datag[2]/Messwertmax[3]*grh, grh)),
                                                                  max(0, min(datag[3]/Messwertmax[4]*grh, grh)),
                                                                  0,0,0,0,0 ]])), axis=0)  # 1.ter Messwert kommt erst als 2. Index in das Array

                for i in range (1, MaxAnzGraphen+1):
                    Graphen[i].updateGraph(i)

                root.update()

app = App(root)

try:

  #if logg: print("Öffne USB-Port: ", Port)
    with serial.Serial(PORT) as ser:
        root.mainloop()
except serial.serialutil.SerialException:
    print ("Keine Daten auf USB (serial.serialutil.SerialException:)")
    root.mainloop()
