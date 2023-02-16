from config_sp import *
from tkinter import *
import math
import time
import serial
import csv
import random

import numpy as np
import sys
import os

logg = 1    # 1.. looging von Meldungen
usbsim = 1  # 1.. statt Daten von USB zu lesen werden Messwerte simuliert für Tests ohne Arduino
LowSamplingGrenze= 1   # wenn mehr als 10x hintereinander die Samplingrate kleiner ist, dann auomatisch Restart
tagnacht= 0     # 0... Tag  / 1... Nacht

#######################################################
### Setze Variablen, die man im GUI noch verändern kann
#######################################################
def GUIReset():
    global tagnacht
    global dockx1
    global dockx2
    global docky1
    global docky2
    global grx1
    global grx2
    global gry1
    global gry2
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
    global AnzahlDerRundinstrumente
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
    global rundRahmenfarbe
    global rundFlächenfarbe
    global rundZeigerfarbe
    global alleSchattenfarbe

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
    wgwertsize= int((wgy2-wgy1)/30)
    wgwertabstand= wgwertsize*2

    # Rundinstrumente: links oben:   x= grx2    y= wgy2
    #                  rechts unten: x= fb      y= docky1
    rundx1= grx2+rand
    rundy1= wgy2+rand
    rundx2= fb-rand
    rundy2= docky1-rand

    AnzahlDerRundinstrumente = 3    # Ausgelegt für drei Rundinstrumente nebeneinander

    rx1 = [0, 0, 0]
    rx2 = [0, 0, 0]
    ry1 = [0, 0, 0]
    ry2 = [0, 0, 0]

    rxm = [0, 0, 0]
    rym = [0, 0, 0]
    rrad = [0, 0, 0]
    rau = [0, 0, 0]

    rst1 = [0, 0, 0]
    rst2 = [0, 0, 0]
    rstt = [0, 0, 0]
    rin = [0, 0, 0]
    rzei = [0, 0, 0]
    rzb = [0, 0, 0]

    # Diese Radiusberechnung gilt für 3 Rundinstrumente nebeneinander (und nur 1 Reihe)
    # hinsichtlich Breite: verfügbare Breite - innere Ränder (zw 1. und 2., zw 2. und 3.) / 3 Rundinstrumente  ... Radius=Druchmesser/2
    # hinsichtlich Höhe: verfügbare Höhe /2
    # tatsächerlicher Radius ist kleinerer Wert, von der möglichen Größe hinsichtlich Breite und Höhe
    rad_i = min(((rundx2-rundx1)-2*rand)/3/2, (rundy2-rundy1)/2)

    for x in range(0, 3):

        rrad = [rad_i, rad_i, rad_i]

    #    rx1 = [rand, rand+rrad[0]*2+rand, rand+rrad[1]*4+rand*3]
    #    rx2 = [rand+rad_i*2, rand+rrad[0]*2+rand+rad_i*2, rand+rrad[1]*4+rand*3+rad_i*2]
    #    ry1 = [rand, rand, rand]
    #    ry2 = [rx2[0], ry2[0], ry2[0]]
        rx1 = [rundx1,           rundx1+rrad[0]*2+rand,    rundx1+rrad[0]*2+rand+rrad[1]*2+rand]
        rx2 = [rx1[0]+rrad[0]*2, rx1[1]+rrad[1]*2,         rx1[2]+rrad[1]*2]
        ry1 = [rundy1,               rundy1,               rundy1]
        ry2 = [rundy1+rx2[0]-rx1[0], rundy1+rx2[1]-rx1[1], rundy1+rx2[2]-rx1[2]]

        rxm = [rx1[0]+(rx2[0]-rx1[0])/2, rx1[1]+(rx2[1]-rx1[1])/2, rx1[2]+(rx2[2]-rx1[2])/2]
        rym = [ry1[0]+(ry2[0]-ry1[0])/2, ry1[1]+(ry2[1]-ry1[1])/2, ry1[2]+(ry2[2]-ry1[2])/2]
        rau = [max(rrad[0]/50,5), max(rrad[1]/50,5), max(rrad[2]/50,5)]

        rst1 = [max(rrad[0]/7,2), max(rrad[1]/7,2), max(rrad[2]/7,2)]
        rst2 = [max(rrad[0]/30,5), max(rrad[1]/30,5), max(rrad[2]/30,5)]
        rstt = [max(rrad[0]/20,12), max(rrad[1]/30,12), max(rrad[2]/40,12)]
        rin = [max(rrad[0]/10,10), max(rrad[1]/10,10), max(rrad[2]/10,10)]
        rzei = [rrad[0]-rst1[0], rrad[1]-rst1[1], rrad[2]-rst1[2]]
        rzb = [max(rzei[0]/20,10), max(rzei[0]/20,10), max(rzei[0]/20,10)]

    rundRahmenfarbe= []
    rundFlächenfarbe= []
    rundZeigerfarbe= []
    alleSchattenfarbe= []
    # 1.ter Werte (Index=0)... Farbe für Tag
    # 2.ter Werte (Index=1)... Farbe für ^Nacht
    rundRahmenfarbe= np.append("red","yellow")
    rundFlächenfarbe= np.append("grey90","grey10")
    rundZeigerfarbe= np.append("red","yellow")
    alleSchattenfarbe= np.append("grey70","grey20")


    if logg: print("Start... fb= ", fb, " fh= ", fh)
    if logg: print("         fbteil= ", fbteil, " fhteil= ", fhteil)
    if logg: print("         dockx1= ", dockx1, " docky1= ", docky1, " dockx2= ", dockx2, " docky2= ", docky2)
    if logg: print("         grx1= ", grx1, " gry1= ", gry1, " grx2= ", grx2, " gry2= ", gry2)
    if logg: print("         wgx1= ", wgx1, " wgy1= ", wgy1, " wgx2= ", wgx2, " wgy2= ", wgy2)
    if logg: print("         rundx1= ", rundx1, " rundy1= ", rundy1, " rundx2= ", rundx2, " rundy2= ", rundy2," rad_i= ", int(rad_i))

#################################################################
### Reset der Anzeige von Rundinstument, Wertegruppen und Graphen
#################################################################
def AnzeigeObjekteReset():

    for Rundinstrument in Rundinstrumente:
        Rundinstrument.deleteRundinstrument()
        Rundinstrument.zeichneRundinstrument()

    for i in range (len(Wertegruppen)):
        Wertegruppen[i].deleteWertegruppe()
        Wertegruppen[i].zeichneWertegruppe(wgx1, wgy1+wgwertabstand*(i+1))

    global Graphen
    for i in range (1, len(Graphen)):
        Graphen[i].posx1= grx1
        Graphen[i].posx2= grx2
        Graphen[i].posy1= gry1+((gry2-gry1)/MaxAnzGraphen)*(i-1)
        Graphen[i].posy2= gry1+((gry2-gry1)/MaxAnzGraphen)*(i  )-rand
        Graphen[i].deleteGraph()
        Graphen[i].zeichneGraph()

#    self.Dockfelder()

#########################
### Globaler Programmtext
#########################

Rundinstrumente = []
Wertegruppen = []
Graphen = []

MaxAnzRundinstrumente = 3
MaxAnzWertegruppen = 9
MaxAnzGraphen = 4

dataRundinstrument = [0,0,0]
History = 20   # Max Anzahl von historischen Werten im Graph
dataGraph = []
Graphenlinie = False

#                      1             2           3           4         5          6         7         8         9
Messwertname=    ["0", "Drehmoment", "Drehzahl", "Leistung", "Schub",  "Gas",     "Temp1",  "Temp2",  "Temp3",  "Temp4"]
Messwerteinheit= ["0", "Ncm",        "U/m",      "kW",       "kg",     "%",       "oC",     "oC",     "oC",     "oC"]
Messwertfarbebg= ["0", "red",        "blue",     "green",    "orange", "magenta", "orange", "orange", "orange", "orange"]
Messwertfarbefg= ["0", "grey0",      "grey90",   "grey0",    "grey0",  "grey0",   "grey0",  "grey0",  "grey0",  "grey0"]


PORT = '/dev/tty.usbmodem1421'

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
        self.dataGraph = []
        self.dataLinie = []
        self.Graphenlinie = False

    def zeichneGraph(self):
        self.dieXAchse = w.create_line(self.posx1, self.posy2, self.posx2, self.posy2, fill= grAchsenFarbe, width= grAchsenDicke)
        self.dieYAchse = w.create_line(self.posx1, self.posy1, self.posx1, self.posy2, fill= grAchsenFarbe, width= grAchsenDicke)

    def deleteGraph(self):
        w.delete(self.dieXAchse)
        w.delete(self.dieYAchse)

    def updateGraph(self, MesswertNr):
        if self.Graphenlinie:
            for Linie in self.dataLinie:
                w.delete(Linie)

        for i in range (0, min(len(dataGraph)-1, History)):
            self.Graphenlinie = True
            self.dataLinie.append(w.create_line(grx2-(i  )*grXsampling, self.posy2-dataGraph[i  ][MesswertNr],
                                                           grx2-(i+1)*grXsampling, self.posy2-dataGraph[i+1][MesswertNr], fill= Messwertfarbebg[MesswertNr], width= grLinienDicke))

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

    def updateWertegruppe(self, WertegruppeWert, WertegruppeEinheit):
        self.EinLabelWert.config(text = str(WertegruppeWert) + " " + WertegruppeEinheit)


class Rundinstrument:

    def __init__(self, Nummer, LabelText, LabelBG, LabelFG, Einheit):

        self.Nr = Nummer - 1     #Wegen Zugriff auf Arrays
        wd = math.pi/2
        self.Einheit = Einheit
        self.LabelText = LabelText
        self.LabelBG = LabelBG
        self.LabelFG = LabelFG

        self.wi = math.pi*0.2

        self.minimiert = False

        self.zeichneRundinstrument()

    def zeichneRundinstrument(self):

        self.derRoteRahmen = w.create_oval(rx1[self.Nr], ry1[self.Nr], rx2[self.Nr], ry2[self.Nr], fill=rundRahmenfarbe[tagnacht])
        self.dieGraueFläche = w.create_oval(rx1[self.Nr]+rau[self.Nr], ry1[self.Nr]+rau[self.Nr], rx2[self.Nr]-rau[self.Nr], ry2[self.Nr]-rau[self.Nr], fill=rundFlächenfarbe[tagnacht])

        self.EinLabelWert = Label(root, text=self.LabelText, bg=self.LabelBG, fg=self.LabelFG, font=("fixedsys", max(int(rrad[self.Nr]/8),10)))
        self.EinLabelWert.pack()
        self.EinLabelWert.place(x=rxm[self.Nr], y=rym[self.Nr]+rrad[self.Nr]*0.4, anchor="c")

        self.wi = math.pi*0.2

        self.dieLinien = []
        while (self.wi < math.pi*1.8):
            self.dieLinien.append(w.create_line(rxm[self.Nr]+math.cos(self.wi+wd)*(rrad[self.Nr]-rst1[self.Nr]), rym[self.Nr]+math.sin(self.wi+wd)*(rrad[self.Nr]-rst1[self.Nr]),rxm[self.Nr]+math.cos(self.wi+wd)*(rrad[self.Nr]-rst2[self.Nr]),rym[self.Nr]+math.sin(self.wi+wd)*(rrad[self.Nr]-rst2[self.Nr]), fill="grey30", width=max(int(rrad[self.Nr]/60),2)))
            self.wi = self.wi + math.pi/rstt[self.Nr]
        self.dasOvalSchatten = w.create_oval(rxm[self.Nr]-rin[self.Nr]+xSchatten, rym[self.Nr]-rin[self.Nr]+ySchatten, rxm[self.Nr]+rin[self.Nr]+xSchatten, rym[self.Nr]+rin[self.Nr]+ySchatten, outline=alleSchattenfarbe[tagnacht], fill=alleSchattenfarbe[tagnacht])
        self.dasOval =         w.create_oval(rxm[self.Nr]-rin[self.Nr],           rym[self.Nr]-rin[self.Nr],           rxm[self.Nr]+rin[self.Nr],           rym[self.Nr]+rin[self.Nr], fill=rundZeigerfarbe[tagnacht])

        self.derStrichSchatten = w.create_line(rxm[self.Nr]+xSchatten, rym[self.Nr]+ySchatten, rxm[self.Nr]+math.cos(self.wi+wd)*(rzei[self.Nr]-2)+xSchatten, rym[self.Nr]+math.sin(self.wi+wd)*(rzei[self.Nr]-2)+xSchatten, fill=alleSchattenfarbe[tagnacht], width=rzb[self.Nr])
        self.derStrich =         w.create_line(rxm[self.Nr],           rym[self.Nr],           rxm[self.Nr]+math.cos(self.wi+wd)*(rzei[self.Nr]-2),           rym[self.Nr]+math.sin(self.wi+wd)*(rzei[self.Nr]-2), fill=rundZeigerfarbe[tagnacht], width=rzb[self.Nr])
        self.EinLabelWert.config(text = str(self.Nr) + " " + self.Einheit)
        root.update()

        self.dieCheckbox = Checkbutton(root, text="", variable=self.minimiert)
        self.dieCheckbox.pack()
        self.dieCheckbox.place(x=rx1[self.Nr], y=ry1[self.Nr], anchor="c")

    def deleteRundinstrument(self):

        w.delete(self.derRoteRahmen)
        w.delete(self.dieGraueFläche)
        self.EinLabelWert.destroy()
        for Linie in self.dieLinien:
            w.delete(Linie)
        w.delete(self.dasOvalSchatten)
        w.delete(self.dasOval)
        w.delete(self.derStrichSchatten)
        w.delete(self.derStrich)
        self.dieCheckbox.destroy()

    def updateRundinstrument(self, Nummer):

        self.Nr = Nummer - 1     #Wegen Zugriff auf Arrays

        w.delete(self.dasOvalSchatten)
        w.delete(self.dasOval)
        w.delete(self.derStrichSchatten)
        w.delete(self.derStrich)

        self.EinLabelWert.config(text = str(dataRundinstrument[self.Nr]) + " " + self.Einheit)

        self.derStrichSchatten = w.create_line(rxm[self.Nr]+xSchatten, rym[self.Nr]+ySchatten, rxm[self.Nr]+math.cos(self.wi+wd)*(rzei[self.Nr]-2)+xSchatten, rym[self.Nr]+math.sin(self.wi+wd)*(rzei[self.Nr]-2)+xSchatten, fill=alleSchattenfarbe[tagnacht], width=rzb[self.Nr])
        self.dasOvalSchatten = w.create_oval(rxm[self.Nr]-rin[self.Nr]+xSchatten, rym[self.Nr]-rin[self.Nr]+ySchatten, rxm[self.Nr]+rin[self.Nr]+xSchatten, rym[self.Nr]+rin[self.Nr]+ySchatten, outline=alleSchattenfarbe[tagnacht], fill=alleSchattenfarbe[tagnacht])
        self.derStrich =         w.create_line(rxm[self.Nr],           rym[self.Nr],           rxm[self.Nr]+math.cos(self.wi+wd)*(rzei[self.Nr]-2),           rym[self.Nr]+math.sin(self.wi+wd)*(rzei[self.Nr]-2), fill=rundZeigerfarbe[tagnacht], width=rzb[self.Nr])
        self.dasOval =         w.create_oval(rxm[self.Nr]-rin[self.Nr],           rym[self.Nr]-rin[self.Nr],           rxm[self.Nr]+rin[self.Nr],           rym[self.Nr]+rin[self.Nr], fill=rundZeigerfarbe[tagnacht])

class App:
    def __init__(self, root):
        frame = Frame(root)
        frame.pack()

        w.create_rectangle(0, 0, fb, fh, fill="grey99")
        w.create_rectangle(dockx1, docky1, dockx2, docky2, fill="grey90")

        self.button = Button(frame, text="QUIT", fg="red", command=frame.quit)
        self.button.pack(side=LEFT)

        self.slogan = Button(frame, text="Start", command=self.LeseUSB)
        self.slogan.pack(side=LEFT)

        self.slogan = Button(frame, text="Restart", command=self.Restart)
        self.slogan.pack(side=LEFT)

        self.slogan = Button(frame, text="<<Teilung", command=self.GUIChangeTeilungL)
        self.slogan.pack(side=LEFT)
        self.slogan = Button(frame, text="Teilung>>", command=self.GUIChangeTeilungR)
        self.slogan.pack(side=LEFT)

        self.slogan = Button(frame, text="Tag/Nacht", command=self.GUIChangeTagNacht)
        self.slogan.pack(side=LEFT)

        if logg: print("init")
        self.Dockfelder()

        global Rundinstrumente
        for i in range (1, MaxAnzRundinstrumente+1):
            Rundinstrumente.append(Rundinstrument(i, Messwertname[i], Messwertfarbebg[i], Messwertfarbefg[i], Messwerteinheit[i]))

        global Wertegruppen
        for i in range (1, MaxAnzWertegruppen+1):
            Wertegruppen.append(c_Wertegruppe(i, Messwertname[i], Messwertfarbebg[i], Messwertfarbefg[i]))
        for i in range (len(Wertegruppen)):
            Wertegruppen[i].zeichneWertegruppe(wgx1, wgy1+wgwertabstand*(i+1))

        global Graphen
        for i in range (1, MaxAnzGraphen+2):
            Graphen.append(c_Graph(i))
        for i in range (1, len(Graphen)):
            Graphen[i].posx1= grx1
            Graphen[i].posx2= grx2
            Graphen[i].posy1= gry1+((gry2-gry1)/MaxAnzGraphen)*(i-1)
            Graphen[i].posy2= gry1+((gry2-gry1)/MaxAnzGraphen)*(i  )-rand
            Graphen[i].zeichneGraph()


        self.LeseUSB()

############################
### Ändern GUI
############################
    def GUIChangeTeilungR(self):
        global fbteil

        if fbteil < 90:
            fbteil= fbteil+10
        else:
            fbteil= 10

        GUIReset()
        AnzeigeObjekteReset()

    def GUIChangeTeilungL(self):
        global fbteil

        if fbteil > 10:
            fbteil= fbteil-10
        else:
            fbteil= 90

        GUIReset()
        AnzeigeObjekteReset()

    def GUIChangeTagNacht(self):
        global tagnacht

        if tagnacht == 0:
            tagnacht = 1
        else:
            tagnacht = 0

        GUIReset()
        AnzeigeObjekteReset()

############################
### Dockfelder zeichnen
############################
    def Dockfelder(self):
        global DockWert11
        global DockWert12

        dockfont="fixedsys"
        docksize= int(dockh/3)

        DockWert11 = Label(root, text="Sampling", bg="grey90", fg="grey0",font=(dockfont, docksize))
        DockWert11.pack()
        DockWert11.place(x=dockx1+rand, y=docky1+dockh*0.5, anchor="w")

        DockWert12 = Label(root, text="Start", bg="grey90", fg="grey0",font=(dockfont, docksize))
        DockWert12.pack()
        DockWert12.place(x=dockx2-rand, y=docky1+dockh*0.5, anchor="e")

###############################################
### Lese USB ein und stelle alle Datenwerte dar
###############################################
    def Restart(self):
        i = 1
        os.execv(sys.executable, ['python3.6'] + sys.argv)

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
        sim0= 10
        First= True
        Startup= False
        LowSampling= 0

        while True:
            global lasttime
            if First:
                First = False
                DockWert12.config(text = "Startzeit " + time.strftime("%H:%M:%S", time.localtime(time.time())))
            sample = float(time.time() - lasttime)
            if sample > 0:
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

            if usbsim:
                sim= [sim0,
                sim0/2,   #                1200-sim0,
                random.randint(100,1200),
                random.randint(0,20),
                random.randint(1,10),
                random.randint(10,150),
                random.randint(10,150),
                random.randint(10,150),
                random.randint(10,150)]
                data = sim
                if sim0<200:
                    sim0 += 2
                else:
                    sim0 += 20
                if sim0 > 1000: sim0= 100
#                time.sleep (0.01)
            else:
                line = ser.readline().decode()
                if logg: print(line)
                data = line.split(';')

            try:
                dataRundinstrument.clear()
                for i, Rundinstrument in enumerate(Rundinstrumente):
                    Rundinstrumente[i].wi=float(int(data[i])+20)/200
                    dataRundinstrument.append(data[i])
                    Rundinstrument.updateRundinstrument(i+1)


                for i in range (len(Wertegruppen)):
                    Wertegruppen[i].updateWertegruppe(float(int(data[i])+0)/1, Messwerteinheit[i+1])

                if len(dataGraph) >= History:
                    dataGraph.pop(0)    # lösche ältersten Messwert
                dataGraph.append([0, data[0]/10, data[1]/10, data[2]/10, 0, 0, 0, 0, 0, 0])  # 1.ter Messwert kommt erst als 2. Index in das Array

                for i in range (1, 4):
                    Graphen[i].updateGraph(i)

                root.update()

            except IndexError:
                print("IndexError")
            except ValueError:
                print("ValueError")

app = App(root)

try:
    with serial.Serial(PORT) as ser:
        root.mainloop()
except serial.serialutil.SerialException:
    print ("Keine Daten auf USB (serial.serialutil.SerialException:)")
    root.mainloop()
