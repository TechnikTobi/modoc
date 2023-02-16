from tkinter import *
import math
import time
import serial
import csv
import random
import numpy as np
import sys
import os
import subprocess
import platform


########
# ToDos:
########
# istPruefstand     wieder einbauen lt e9h
# Konfigdateien von USB Stick auf Raspberry Speicher reinladen, wenn USB Stick angesteckt ist
# UPM Messdiagramm mit GasBox-Steuerung und Ausgabe auf PDF oder so
# Kalibrieren mit Toleranz-Prozenten
# nice to have: pro Messwert separate Glättung (Tiefe Ringbuffer)


#############################
# Raspberry Hardware Hinweise
#############################
gpioPinFuerArduinoKommunikation = 11    # Pin 11 für Kabel zum Arduino "ready für USB - Datenübernahme" ... logisch: GPIO17
                                        # (Pin 11 ist die physikalische Pinordnung und dort ist der logische Pin: GPIO17)

override = False         # True um zb am Raspberry usbsim zu setzen
                         # muss auf False sein, um am Raspberry real zu laufen !!!!

if not override:
    if platform.system() == 'Darwin':           # Darwin = MacOS
        from PIL import Image, ImageTk
        import keyboard
        rasp = 0
        usbsim = 1
    else:                                       # Raspberry
        rasp = 1
        usbsim = 0
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(gpioPinFuerArduinoKommunikation, GPIO.OUT)
        GPIO.output(gpioPinFuerArduinoKommunikation, GPIO.LOW)
else:
    #override
    rasp = 1
    usbsim = 1

fontSizeFaktor = 0.7
if rasp:
    fontSizeFaktor = 0.65

# Da bei jedem Programmstart sich die Hoehe verändert
fensterHoehenAbzug = 0
if rasp:
    fensterHoehenAbzug = 2
else:
    fensterHoehenAbzug = 6

adcdirekt = 0
istPruefstand = 1                       # 1.. Prüfstand / 0.. Makerbeam-Test-Aufbau bei SP
einheitSchub = 1                        # 1 .. kg, 1000 .. g
History = 50
LowSamplingGrenze = 1
# logg = True
logg = False

# Allgemeine Funktionen
def stufenFunktion(eingabe):            # für Hilfslinienwerte beim Graphen
    if(eingabe <= 0.1):
        print("WARNUNG ", eingabe)
        return 0.1
    elif(eingabe <= 0.2):
        return 0.2
    elif(eingabe <= 0.5):
        return 0.5
    elif(eingabe <= 1):
        return 1
    elif(eingabe <= 2):
        return 2
    elif(eingabe <= 5):
        return 5
    elif(eingabe <= 10):
        return 10
    elif(eingabe <= 20):
        return 20
    elif(eingabe <= 50):
        return 50
    elif(eingabe <= 100):
        return 100
    elif(eingabe <= 200):
        return 200
    elif(eingabe <= 500):
        return 500
    elif(eingabe <= 1000):
        return 1000
    elif(eingabe <= 2000):
        return 2000
    elif(eingabe <= 5000):
        return 5000
    elif(eingabe <= 10000):
        return 10000
    elif(eingabe <= 20000):
        return 20000
    elif(eingabe <= 50000):
        return 50000
    elif(eingabe <= 100000):
        return 100000
    elif(eingabe <= 200000):
        return 200000
    elif(eingabe <= 500000):
        return 500000
    elif(eingabe <= 1000000):
        return 1000000
    elif(eingabe <= 2000000):
        return 2000000
    elif(eingabe <= 5000000):
        return 5000000
    elif(eingabe <= 10000000):
        return 10000000
    elif(eingabe <= 20000000):
        return 20000000
    elif(eingabe <= 50000000):
        return 50000000
    elif(eingabe <= 100000000):
        return 100000000
    elif(eingabe <= 200000000):
        return 200000000
    elif(eingabe <= 500000000):
        return 500000000
    else:
        print("Zu großer Abstand zwischen Hilfslinien")



def Luminance(eingabeHexFarbe):                 # Abhängig von Helligkeit der Textboxhintergrundfarbe wird Text Schwarz oder Weiß geschrieben
    red = int(eingabeHexFarbe[1 : 3], 16)
    green = int(eingabeHexFarbe[3 : 5], 16)
    blue = int(eingabeHexFarbe[5 : 7], 16)
    #if (0.2126*red + 0.7152*green + 0.0722*blue) > 50:
    #print(math.sqrt( 0.299*pow(red,2) + 0.587*pow(green,2) + 0.114*pow(blue,2) ))
    # print(0.299*red + 0.587*green + 0.114*blue)
    if (math.sqrt( 0.299*pow(red,2) + 0.587*pow(green,2) + 0.114*pow(blue,2) )) > 130:
        return "#000000"            # Schwarz
    else:
        return "#ffffff"            # Weiß


def Tempmap(temp_eich,dig):

    if adcdirekt == 0:
        if dig == 0: return 0               # Arcduino sendet Wert = 0, wenn kein Sensor angesteckt --> dann 0°C anzeigen als default.
        dig = dig + temp_eich
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
        e = dig + temp_eich    # Direkt für Tests und Eichung den ADC Wert (0..1023) anzeigen ABER auch mit Berücksichtigung von temp_eich (aus config_modoc.csv)
    if adcdirekt == 2:
        e = dig                # Direkt für Tests und Eichung den ADC Wert (0..1023) anzeigen

    return e

class Messobjekt:

    def __init__(self, eingabeMesswertName, eingabeMesswertEinheit, eingabeMinimalerMesswert, eingabeMaximalerMesswert, eingabeMinimalerYachsenWert, eingabeMaximalerYachsenWert, eingabeSkalenmax, eingabeSkalenIncLabel, eingabeSkalenIncStrich, eingabeIndexInDataStream, eingabeIstTagFarbe, eingabeIstNachtFarbe, eingabeGlättung, eingabeZugriffAufApp):

        self.MesswertName = eingabeMesswertName
        self.MesswertEinheit = eingabeMesswertEinheit

        self.MinimalerMesswert = eingabeMinimalerMesswert
        self.MaximalerMesswert = eingabeMaximalerMesswert

        self.MinimalerYachsenWert = eingabeMinimalerYachsenWert     # wird bei Graphen-Skalierung verändert
        self.MaximalerYachsenWert = eingabeMaximalerYachsenWert

        self.Skalenmax = eingabeSkalenmax
        self.SkalenIncLabel = eingabeSkalenIncLabel
        self.SkalenIncStrich = eingabeSkalenIncStrich

        self.IndexInDataStream = eingabeIndexInDataStream           # Index im USB - Datenstream vom Arduino / Erster = 0

        self.istTagFarbe = eingabeIstTagFarbe
        self.istNachtFarbe = eingabeIstNachtFarbe

        self.meineGlättung = eingabeGlättung                        # Tiefe für Glättungsringbuffer / 1.3.2020: alle noch gleich

        self.value = 0                                              # aktueller Messwert
        self.ringbuffer = np.array([])                              # für Glättung

        self.zugriffAufApp = eingabeZugriffAufApp

    def updateGlaettung(self, eingabeGlättung):
        self.meineGlättung = eingabeGlättung
        if self.meineGlättung == 0:
            self.ringbuffer = np.array([])
        else:
            while(self.ringbuffer.size > self.meineGlättung):         # Wenn Glättung kleiner als vorher -> Ringbuffer beschneiden
                self.ringbuffer = np.delete(self.ringbuffer, 0)


    def refreshYourValue(self, eingabeDataStream, eingabeModocKonstanten):  # wird pro Messobjekt aufgerufen, nimmt aus USB Stream den Arduino-Wert und Eicht,... speichert in .Value
        if self.IndexInDataStream < 5:
            if self.IndexInDataStream == 0: # Drehzahl
                if eingabeDataStream[self.IndexInDataStream] > 0:
                    self.value = int((eingabeModocKonstanten["upm_eich1"] + (eingabeModocKonstanten["upm_eich2"] - eingabeDataStream[self.IndexInDataStream]) * eingabeModocKonstanten["upm_eich3"]) / eingabeDataStream[self.IndexInDataStream])         # Eichung UPM in 1/min
                else:
                    self.value = 0

            if self.IndexInDataStream == 1: # Drehmoment
                if logg: print(self.MesswertName + ": " + str(eingabeDataStream[self.IndexInDataStream]), end = "")
                self.value = int(eingabeDataStream[self.IndexInDataStream] / eingabeModocKonstanten["drehmoment_eich1"] - eingabeModocKonstanten["drehmoment_eich2"]) + eingabeModocKonstanten["drehmoment_kal"]

            if self.IndexInDataStream == 2: # Schub
                if logg: print("       " + self.MesswertName + ": " + str(eingabeDataStream[self.IndexInDataStream]))
                self.value = int((eingabeDataStream[self.IndexInDataStream] / eingabeModocKonstanten["schub_eich1"] - eingabeModocKonstanten["schub_eich2"]) * einheitSchub) + eingabeModocKonstanten["schub_kal"]

            if self.IndexInDataStream == 3: # Leistung
                # self.value = int(2 * math.pi * eingabeDataStream[1]/100 * eingabeDataStream[0]/60)
                self.value = int (2 * math.pi * self.zugriffAufApp.MesswertObjekte["Drehmoment"].value / 100 * self.zugriffAufApp.MesswertObjekte["Drehzahl"].value / 60 )

            if self.IndexInDataStream == 4: # Gas (Wird vorlaeufig auf Null gesetzt)
                self.value = 0
                #self.value = eingabeDataStream[self.IndexInDataStream]

        elif self.IndexInDataStream < 15:
            if self.IndexInDataStream == 9:
                self.value = Tempmap(eingabeModocKonstanten["temp_eich1"], eingabeDataStream[self.IndexInDataStream])
            if self.IndexInDataStream == 10:
                self.value = Tempmap(eingabeModocKonstanten["temp_eich2"], eingabeDataStream[self.IndexInDataStream])
            if self.IndexInDataStream == 11:
                self.value = Tempmap(eingabeModocKonstanten["temp_eich3"], eingabeDataStream[self.IndexInDataStream])
            if self.IndexInDataStream == 12:
                self.value = Tempmap(eingabeModocKonstanten["temp_eich4"], eingabeDataStream[self.IndexInDataStream])
            if self.IndexInDataStream == 14:
                if usbsim == 0:
                    tempFile = open ("/sys/class/thermal/thermal_zone0/temp")
                    self.value = tempFile.read()
                    tempFile.close()
                    self.value = int(float(self.value)/1000)
                else:
                    self.value = 99
            if self.IndexInDataStream == 27: # Eichung VCC Spannung in Volt
                self.value = int(10 * eingabeDataStream[self.IndexInDataStream] / eingabeModocKonstanten["vccspannung_eich1"] - eingabeModocKonstanten["vccspannung_eich2"]) / 10

        elif self.IndexInDataStream < 35:
            self.value = -1

        elif self.IndexInDataStream < 42:
            if self.IndexInDataStream != 40:
                self.value = eingabeDataStream[self.IndexInDataStream]

        elif self.IndexInDataStream < 49:
            if self.IndexInDataStream == 42:
                self.value = Tempmap(eingabeModocKonstanten["temp_eich5"], eingabeDataStream[self.IndexInDataStream])
            if self.IndexInDataStream == 43:
                self.value = Tempmap(eingabeModocKonstanten["temp_eich6"], eingabeDataStream[self.IndexInDataStream])
            if self.IndexInDataStream == 44:
                self.value = Tempmap(eingabeModocKonstanten["temp_eich7"], eingabeDataStream[self.IndexInDataStream])
            if self.IndexInDataStream == 45:
                self.value = Tempmap(eingabeModocKonstanten["temp_eich8"], eingabeDataStream[self.IndexInDataStream])
        else:
            self.value = -1

        self.value = int(self.value*100)/100

        if self.meineGlättung > 0:

            durchschnitt = np.mean(self.ringbuffer)
            selfValueUeberschreiben = True
            
            if durchschnitt > 0:
                    if self.value/durchschnitt > 1.97 or self.value/durchschnitt < 0.5:
                        selfValueUeberschreiben = False
                        self.ringbuffer = np.array([])

            self.ringbuffer = np.append(self.ringbuffer, [self.value])
            if (self.ringbuffer.size > self.meineGlättung):
                self.ringbuffer = np.delete(self.ringbuffer, 0)

            if selfValueUeberschreiben:
                self.value = np.mean(self.ringbuffer)
                self.value = int(self.value*100)/100


class Rundinstrument:

    def __init__(self, eingabeRoot, eingabeCanvas, eingabeMessobjekt, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeRadius, eingabeSchattenXoffset, eingabeSchattenYoffset):

        self.root = eingabeRoot
        self.meinCanvas = eingabeCanvas
        self.meinMessobjekt = eingabeMessobjekt

        self.schattenXoffset = eingabeSchattenXoffset
        self.schattenYoffset = eingabeSchattenYoffset

        self.update(eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeRadius)

        # Farben
        self.farbeRundinstrumentBackground = None
        self.farbeRundinstrumentRahmen = None
        self.farbeRundinstrumentLabel = None
        self.farbeRundinstrumentSchatten = None
        self.farbeRundinstrumentLinie = None
        self.farbeRundinstrumentZeiger = None

        self.farbeRundinstrumentLabelForeground = None # Text Farbe
        self.farbeRundinstrumentLabelBackground = None
        self.setRundinstrumentColorScheme(True)

        self.winkelKonstante = math.pi/2
        self.einheit = self.meinMessobjekt.MesswertEinheit
        self.name = self.meinMessobjekt.MesswertName
        self.LabelText = "-"

        self.winkelHilfe = math.pi*0.2

        self.SkalenLabel = np.array([])
        self.dieLinien = np.array([])

    def update(self, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeRadius):    # Wenn sich Rundinstrument in Position ändert, dann hier neue Parameter bestimmen (aber nicht neu zeichnen)
        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2
        self.radius = eingabeRadius

        self.mittelpunktX = self.posX1 + (self.posX2-self.posX1)/2
        self.mittelpunktY = self.posY1 + (self.posY2-self.posY1)/2

        self.zeigerKreisRadius = max(self.radius*0.65, 10)
        self.graueFlächeRadius = max(self.radius/25,5)

        # "Anfang" und "Ende" im Sinne von Zeichnen der Striche von Außen nach Innen
        self.strichAnfangDistanzRand = max(self.radius/45, 5)
        self.strichEndeDistanzRand = max(self.radius/11, 2)

        self.zeigerLaenge = self.radius-self.strichEndeDistanzRand
        self.zeigerBreite = max(self.zeigerLaenge/10, 6)

    def updateSchatten(self, eingabeSchattenXoffset, eingabeSchattenYoffset):           # nur wenn neuer Benutzer geladen wird (der anderen Schatten definiert haben kann)
        self.schattenXoffset = eingabeSchattenXoffset
        self.schattenYoffset = eingabeSchattenYoffset


    def setRundinstrumentColorScheme(self, istTag):
        if istTag:
            self.farbeRundinstrumentBackground = "grey90"
            self.farbeRundinstrumentRahmen = "red"
            self.farbeRundinstrumentLabel = "grey10"
            self.farbeRundinstrumentSchatten = "#d2d2d2"
            self.farbeRundinstrumentLinie = "grey30"
            self.farbeRundinstrumentZeiger = "red"

            self.farbeRundinstrumentGraueFläche1 = "#fafafa"
            self.farbeRundinstrumentGraueFläche2 = "#f0f0f0"
            self.farbeRundinstrumentGraueFläche3 = "#e6e6e6"
            self.farbeRundinstrumentGraueFläche4 = "#dcdcdc"
            self.farbeRundinstrumentGraueFläche5 = "#d2d2d2"

            self.farbeRundinstrumentLabelBackground = self.meinMessobjekt.istTagFarbe

            self.farbeRundinstrumentLabelForeground = "black"


        else:
            self.farbeRundinstrumentBackground = "grey5"
            self.farbeRundinstrumentRahmen = "#B01010"
            self.farbeRundinstrumentLabel = "grey99"
            self.farbeRundinstrumentSchatten = "#212121"
            self.farbeRundinstrumentLinie = "grey70"
            self.farbeRundinstrumentZeiger = "#B01010"

            self.farbeRundinstrumentGraueFläche1 = "#212121"
            self.farbeRundinstrumentGraueFläche2 = "#2b2b2b"
            self.farbeRundinstrumentGraueFläche3 = "#353535"
            self.farbeRundinstrumentGraueFläche4 = "#3f3f3f"
            self.farbeRundinstrumentGraueFläche5 = "#494949"

            self.farbeRundinstrumentLabelBackground = self.meinMessobjekt.istNachtFarbe

            self.farbeRundinstrumentLabelForeground = "white"

        #self.farbeRundinstrumentLabelForeground = Luminance(self.farbeRundinstrumentLabelBackground)

    def zeichnen(self):

        self.derRoteRahmen = self.meinCanvas.create_oval(
            self.posX1,
            self.posY1,
            self.posX2,
            self.posY2,
            fill = self.farbeRundinstrumentRahmen,
            width = 0,
        )


        self.dieGraueFläche1 = self.meinCanvas.create_oval(
            self.posX1 + self.graueFlächeRadius/2,
            self.posY1 + self.graueFlächeRadius/2,
            self.posX2 - self.graueFlächeRadius/2,
            self.posY2 - self.graueFlächeRadius/2,
            fill = self.farbeRundinstrumentGraueFläche1,
            width = 0
        )

        self.dieGraueFläche2 = self.meinCanvas.create_oval(
            self.posX1 + self.graueFlächeRadius*3.5,
            self.posY1 + self.graueFlächeRadius*3.5,
            self.posX2 - self.graueFlächeRadius*3.5,
            self.posY2 - self.graueFlächeRadius*3.5,
            fill = self.farbeRundinstrumentGraueFläche2,
            width = 0
        )

        self.dieGraueFläche3 = self.meinCanvas.create_oval(
            self.posX1 + self.graueFlächeRadius*5.5,
            self.posY1 + self.graueFlächeRadius*5.5,
            self.posX2 - self.graueFlächeRadius*5.5,
            self.posY2 - self.graueFlächeRadius*5.5,
            fill = self.farbeRundinstrumentGraueFläche3,
            width = 0
        )

        self.dieGraueFläche4 = self.meinCanvas.create_oval(
            self.posX1 + self.graueFlächeRadius*6.75,
            self.posY1 + self.graueFlächeRadius*6.75,
            self.posX2 - self.graueFlächeRadius*6.75,
            self.posY2 - self.graueFlächeRadius*6.75,
            fill = self.farbeRundinstrumentGraueFläche4,
            width = 0
        )

        self.dieGraueFläche5 = self.meinCanvas.create_oval(
            self.posX1 + self.graueFlächeRadius*7.75,
            self.posY1 + self.graueFlächeRadius*7.75,
            self.posX2 - self.graueFlächeRadius*7.75,
            self.posY2 - self.graueFlächeRadius*7.75,
            fill = self.farbeRundinstrumentGraueFläche5,
            width = 0
        )



        self.EinLabelWert = Label(
            self.root,
            text = self.LabelText,
            bg = self.farbeRundinstrumentLabelBackground,
            fg = self.farbeRundinstrumentLabelForeground,
            font = ("Piboto", int(fontSizeFaktor*max(int(self.radius/5),10)))
        )
        self.EinLabelWert.pack()
        self.EinLabelWert.place(
            x = self.mittelpunktX,
            y = self.mittelpunktY + self.radius * 0.12,
            anchor="c"
        )

        self.EinLabelWert2 = Label(
            self.root,
            text = self.LabelText,
            bg = self.farbeRundinstrumentLabelBackground,
            fg = self.farbeRundinstrumentLabelForeground,
            font = ("Piboto", int(fontSizeFaktor*max(int(self.radius/5),10)))
        )
        self.EinLabelWert2.pack()
        self.EinLabelWert2.place(
            x = self.mittelpunktX,
            y = self.mittelpunktY - self.radius * 0.12,
            anchor="c"
        )

        self.SkalenLabel = np.array([])
        self.dieLinien = np.array([])
        self.winkelHilfe = math.pi*0.2

        i = 0;
        labinc = (self.meinMessobjekt.Skalenmax - self.meinMessobjekt.MinimalerMesswert)/self.meinMessobjekt.SkalenIncLabel

        while (self.winkelHilfe <= math.pi * 1.9):

            lab = self.meinMessobjekt.MinimalerMesswert + labinc * i

            self.SkalenLabel = np.append(self.SkalenLabel, [self.meinCanvas.create_text(
                (
                    self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichEndeDistanzRand * 2.25),
                    self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichEndeDistanzRand * 2.25)
                ),
                anchor = "c",
                text = str(int(lab)),
                fill = self.farbeRundinstrumentLabel,
                font = ("Piboto", int(fontSizeFaktor*max(int(self.radius/9),2)))
            )])

            self.dieLinien = np.append(self.dieLinien, [self.meinCanvas.create_line(
                self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichEndeDistanzRand * 1.5),
                self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichEndeDistanzRand * 1.5),
                self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichAnfangDistanzRand),
                self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichAnfangDistanzRand),
                fill=self.farbeRundinstrumentLinie,
                width=max(int(self.radius/80),2)
            )])

            self.winkelHilfe = self.winkelHilfe + math.pi*1.8/(self.meinMessobjekt.SkalenIncLabel+1)
            i += 1

        self.winkelHilfe = math.pi*0.2
        while (self.winkelHilfe <= math.pi * 1.9):
            self.dieLinien = np.append(self.dieLinien, [self.meinCanvas.create_line(
                self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichEndeDistanzRand*0.8),
                self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichEndeDistanzRand*0.8),
                self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichAnfangDistanzRand),
                self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichAnfangDistanzRand),
                fill=self.farbeRundinstrumentLinie,
                width=max(int(self.radius/100),1)
            )])
            self.winkelHilfe = self.winkelHilfe + math.pi*1.8/(self.meinMessobjekt.SkalenIncStrich+1)


        self.EinLabelWert.config(text = "Hallo" + " " + self.einheit)
        self.EinLabelWert2.config(text = self.name)

        self.zeichneBewegicheTeile()

    def delete(self):

        self.meinCanvas.delete(self.derRoteRahmen)

        self.meinCanvas.delete(self.dieGraueFläche1)
        self.meinCanvas.delete(self.dieGraueFläche2)
        self.meinCanvas.delete(self.dieGraueFläche3)
        self.meinCanvas.delete(self.dieGraueFläche4)
        self.meinCanvas.delete(self.dieGraueFläche5)

        self.EinLabelWert.destroy()
        self.EinLabelWert2.destroy()

        for Linie in np.nditer(self.dieLinien):
            self.meinCanvas.delete(int(Linie))

        for i in range(0, self.SkalenLabel.size):
            #self.SkalenLabel[i].destroy()
            self.meinCanvas.delete(int(self.SkalenLabel[i]))

        self.meinCanvas.delete(self.zeigerKreis)
        self.meinCanvas.delete(self.derStrichSchatten)
        self.meinCanvas.delete(self.derStrich)

    def updateAnzeige(self):

        self.meinCanvas.delete(self.zeigerKreis)
        self.meinCanvas.delete(self.derStrichSchatten)
        self.meinCanvas.delete(self.derStrich)

        try:
            self.EinLabelWert.config(text = str(int(self.meinMessobjekt.value)) + " " + self.einheit)
            self.EinLabelWert2.config(text = self.name)
        except:
            print("huhu")

        self.zeichneBewegicheTeile()

    def zeichneBewegicheTeile(self):

        self.winkelHilfe = float(int(self.meinMessobjekt.value) / self.meinMessobjekt.MaximalerMesswert * math.pi*1.6 + math.pi*0.2)

        self.derStrichSchatten = self.meinCanvas.create_line(
            self.mittelpunktX + self.schattenXoffset,
            self.mittelpunktY + self.schattenYoffset,
            self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.zeigerLaenge - 2) + self.schattenXoffset,
            self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.zeigerLaenge - 2) + self.schattenXoffset,
            fill = self.farbeRundinstrumentSchatten,
            width = self.zeigerBreite
        )

        self.derStrich = self.meinCanvas.create_line(
            self.mittelpunktX,
            self.mittelpunktY,
            self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.zeigerLaenge - 2),
            self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.zeigerLaenge - 2),
            fill = self.farbeRundinstrumentZeiger,
            width = self.zeigerBreite,
        )

        self.zeigerKreis = self.meinCanvas.create_oval(
            self.mittelpunktX - self.zeigerKreisRadius,
            self.mittelpunktY - self.zeigerKreisRadius,
            self.mittelpunktX + self.zeigerKreisRadius,
            self.mittelpunktY + self.zeigerKreisRadius,
            fill = self.farbeRundinstrumentLabelBackground,
            #outline = self.farbeRundinstrumentZeiger,
            #width = 4
            width = 0
        )



class Hilfslinien:

    # Konstruktor fuer ein Hilfslinien Objekt
    # Ein Hilfslinien Objekt besteht aus mehreren Hilfslinien fuer ein Graphen  Objekt
    def __init__(self, eingabeCanvas, eingabeAbstandZumRand, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeYachseMaxWert, eingabeYachseMinWert, eingabeHilfslinienDicke):

        self.farbeHilfslinie = None
        self.farbeHilfslinienLabelsForeground = None

        self.meinCanvas = eingabeCanvas
        self.abstandZumRand = eingabeAbstandZumRand

        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2

        self.yAchseMaxWert = eingabeYachseMaxWert
        self.yAchseMinWert = eingabeYachseMinWert
        self.hilfslinienDicke = eingabeHilfslinienDicke
        self.linien = np.array([])
        self.labels = np.array([])

        self.genauerAbstandZwischenZweiHilfslinien = (self.yAchseMaxWert - self.yAchseMinWert)/10                   # erster Ansatz: 10 Hilfslinien
        self.logischerAbstandZwischenZweiHilfslinien = stufenFunktion(self.genauerAbstandZwischenZweiHilfslinien)   # fürs wirkliche Zeichnen dann...

    def setHilfslinienColorScheme(self, istTag):
        if istTag:
            self.farbeHilfslinie = "black"
            self.farbeHilfslinienLabelsForeground = "black"
        else:
            self.farbeHilfslinie = "white"
            self.farbeHilfslinienLabelsForeground = "white"

    def zeichnen(self):

        if logg: print("HALLO")
        if logg: print(self.yAchseMinWert)
        if logg: print(self.yAchseMaxWert)

        # Bestimmen des Abstands zwischen X-Achse und erster Hilfslinie
        yAchseMin = self.yAchseMinWert
        logischerAbstandZwischenAchseUndErsterHilfslinie = 0
        if yAchseMin >= 0:
            if yAchseMin < self.logischerAbstandZwischenZweiHilfslinien:
                logischerAbstandZwischenAchseUndErsterHilfslinie = self.logischerAbstandZwischenZweiHilfslinien - yAchseMin
            else:
                while(yAchseMin >= self.logischerAbstandZwischenZweiHilfslinien):
                    yAchseMin = yAchseMin - self.logischerAbstandZwischenZweiHilfslinien
                logischerAbstandZwischenAchseUndErsterHilfslinie = self.logischerAbstandZwischenZweiHilfslinien - yAchseMin
        else:
            if -yAchseMin < self.logischerAbstandZwischenZweiHilfslinien:
                logischerAbstandZwischenAchseUndErsterHilfslinie = abs(yAchseMin)
            else:
                while(-yAchseMin >= self.logischerAbstandZwischenZweiHilfslinien):
                    yAchseMin = yAchseMin + self.logischerAbstandZwischenZweiHilfslinien
                logischerAbstandZwischenAchseUndErsterHilfslinie = -yAchseMin


        # Umrechnen des Abstands in Pixel
        if((self.yAchseMaxWert)-self.yAchseMinWert != 0):
            abstandsBerechnungsFaktor = (self.posY2-self.posY1)/((self.yAchseMaxWert)-self.yAchseMinWert)
        else:
            abstandsBerechnungsFaktor = (self.posY2-self.posY1)/((self.yAchseMaxWert)-self.yAchseMinWert+0.001)
        pixelHilfslinienYstart = self.posY2 - (logischerAbstandZwischenAchseUndErsterHilfslinie * abstandsBerechnungsFaktor)
        pixelAbstandZwischenZweiHilfslinien = (self.logischerAbstandZwischenZweiHilfslinien * abstandsBerechnungsFaktor)

        self.labels = np.array([])

        # For Schleife die so oft wiederholt wird wie es Hilfslinien geben kann
        i = 0
        while((pixelHilfslinienYstart - i*pixelAbstandZwischenZweiHilfslinien) >= self.posY1):

            # Hinzufuegen der Hiflslinien zum Array
            self.linien = np.append (self.linien, [self.meinCanvas.create_line(
                self.posX1,
                pixelHilfslinienYstart - i*pixelAbstandZwischenZweiHilfslinien,
                self.posX2,
                pixelHilfslinienYstart - i*pixelAbstandZwischenZweiHilfslinien,
                fill= self.farbeHilfslinie,
                width= self.hilfslinienDicke,
                dash=(1,5)
            )])

            self.labels = np.append(self.labels, [self.meinCanvas.create_text(
                    (
                        self.posX1 - self.abstandZumRand * 0.5,
                        pixelHilfslinienYstart - i*pixelAbstandZwischenZweiHilfslinien
                    ),
                anchor = "e",
                text = str( int( 100*(self.yAchseMinWert + logischerAbstandZwischenAchseUndErsterHilfslinie + i*self.logischerAbstandZwischenZweiHilfslinien) )/100 ),
                font = ("Piboto", int(fontSizeFaktor*18)),
                fill = self.farbeHilfslinienLabelsForeground
            )])

            i = i+1

    def update(self, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeYachseMaxWert, eingabeYachseMinWert, eingabeAbstandZumRand):
        self.yAchseMaxWert = eingabeYachseMaxWert
        self.yAchseMinWert = eingabeYachseMinWert
        if logg: print(self.yAchseMinWert, self.yAchseMaxWert)
        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2
        self.abstandZumRand = eingabeAbstandZumRand

        self.genauerAbstandZwischenZweiHilfslinien = (self.yAchseMaxWert - self.yAchseMinWert)/10
        self.logischerAbstandZwischenZweiHilfslinien = stufenFunktion(self.genauerAbstandZwischenZweiHilfslinien)

    def delete(self):
        for Linie in np.nditer(self.linien):
            self.meinCanvas.delete(int(Linie))
        self.linien = np.array([])

        for i in range(0, self.labels.size):
            self.meinCanvas.delete(int(self.labels[i]))
        self.labels = np.array([])


class WertegruppenElement:

    def __init__(self, eingabeRoot, eingabeCanvas, eingabeWerteX, eingabeWerteY, eingabeMessobjekt, eingabeFontSize):

        self.root = eingabeRoot
        self.meinCanvas = eingabeCanvas
        self.meinMessobjekt = eingabeMessobjekt

        self.einheit = self.meinMessobjekt.MesswertEinheit
        self.name = self.meinMessobjekt.MesswertName

        self.wertePosX = eingabeWerteX
        self.wertePosY = eingabeWerteY

        self.fontSize = eingabeFontSize

        self.farbeWertegruppeBackground = None
        self.farbeWertegruppeForeground = None
        self.setWertegruppenElementColorScheme(True)

    def setWertegruppenElementColorScheme(self, istTag):
        if istTag:
            self.farbeWertegruppeLinie = self.meinMessobjekt.istTagFarbe
            self.farbeWertegruppeBackground = "#E9E9E9"
            self.farbeWertegruppeForeground = "#000000"
        else:
            self.farbeWertegruppeLinie = self.meinMessobjekt.istNachtFarbe
            self.farbeWertegruppeBackground = "#212121"
            self.farbeWertegruppeForeground = "#FFFFFF"

    def zeichnen(self):

        self.einRechteck = self.meinCanvas.create_rectangle(
            self.wertePosX,
            self.wertePosY,
            self.wertePosX+self.fontSize*11,
            self.wertePosY+self.fontSize*1.25+1,
            fill = self.farbeWertegruppeBackground,
            width = 0
        )

        percentage = 0          # Breite des Farbbalkens

        self.nochEinRechteck = self.meinCanvas.create_rectangle(
            self.wertePosX,
            self.wertePosY,
            self.wertePosX+self.fontSize*11*percentage,
            self.wertePosY+self.fontSize*1.25+1,
            fill = self.farbeWertegruppeLinie,
            width = 0
        )


        self.eineLinie = self.meinCanvas.create_rectangle(
            self.wertePosX,
            self.wertePosY,
            self.wertePosX+self.fontSize/5,
            self.wertePosY+self.fontSize*1.25+1,
            fill = self.farbeWertegruppeLinie,
            width = 0
        )

        self.einLabelWert = self.meinCanvas.create_text(
            (
                self.wertePosX + self.fontSize/5 + 1,
                self.wertePosY
            ),
            anchor = "nw",
            text="0",
            fill = self.farbeWertegruppeForeground,
            font = ("Piboto", int(fontSizeFaktor*self.fontSize))
        )

        self.einLabelName = self.meinCanvas.create_text(
            (
                self.wertePosX+self.fontSize*11,
                self.wertePosY
            ),
            anchor = "ne",
            text = "(" + self.name + ")",
            fill = self.farbeWertegruppeForeground,
            font = ("Piboto", int(fontSizeFaktor*self.fontSize))
        )

    def delete(self):
        self.meinCanvas.delete(self.eineLinie)
        self.meinCanvas.delete(self.einRechteck)
        self.meinCanvas.delete(self.nochEinRechteck)
        self.meinCanvas.delete(self.einLabelWert)
        self.meinCanvas.delete(self.einLabelName)

    def update(self, eingabeWerteX, eingabeWerteY, eingabeFontSize):
        self.wertePosX = eingabeWerteX
        self.wertePosY = eingabeWerteY
        self.fontSize = eingabeFontSize

    # Aktualisiert nur die Anzeige, fordert das Messobjekt aber NICHT dazu auf, dessen Wert vom Datastream zu refreshen
    def updateAnzeige(self):
        self.meinCanvas.delete(self.nochEinRechteck)

        try:
            percentage = (min(self.meinMessobjekt.MaximalerMesswert,max(self.meinMessobjekt.value, self.meinMessobjekt.MinimalerMesswert))-self.meinMessobjekt.MinimalerMesswert)/(self.meinMessobjekt.MaximalerMesswert - self.meinMessobjekt.MinimalerMesswert)
        except:
            percentage = 0

        self.nochEinRechteck = self.meinCanvas.create_rectangle(
            self.wertePosX,
            self.wertePosY,
            self.wertePosX+self.fontSize*11*percentage,
            self.wertePosY+self.fontSize*1.25+1,
            fill = self.farbeWertegruppeLinie,
            width = 0
        )

        self.meinCanvas.delete(self.einLabelWert)
        self.einLabelWert = self.meinCanvas.create_text(
            (
                self.wertePosX + self.fontSize/5 + 3,
                self.wertePosY + 1
            ),
            anchor = "nw",
            #text=str((self.meinMessobjekt.value)) + " " + self.einheit + " (" + self.name + ")",
            text=str((self.meinMessobjekt.value)) + " " + self.einheit,
            fill = self.farbeWertegruppeForeground,
            font = ("Piboto", int(fontSizeFaktor*self.fontSize)),
        )

        self.meinCanvas.delete(self.einLabelName)
        self.einLabelName = self.meinCanvas.create_text(
            (
                self.wertePosX+self.fontSize*11,
                self.wertePosY
            ),
            anchor = "ne",
            text = "(" + self.name + ")",
            fill = self.farbeWertegruppeForeground,
            font = ("Piboto", int(fontSizeFaktor*self.fontSize))
        )


class Wertegruppe:          # Das sind alle Wertegruppen die "rechts oben" angezeigt weren in Spalten/Zeilen

    def __init__(self, eingabeRoot, eingabeCanvas, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeMessobjekteArray):
        self.root = eingabeRoot
        self.meinCanvas = eingabeCanvas

        self.WertegruppenElemente = np.array([])
        self.spaltenAnzahl = 1
        self.fontSize = 0
        self.horizontalerAbstand = 0
        self.vertikalerAbstand = 2
        self.anzahlWertegruppenElemente = len(eingabeMessobjekteArray)

        self.update(eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2)

        labelCounter = 0 # wichtig fuer Abstand zwischen den Labels
        for einMessobjekt in eingabeMessobjekteArray:
            self.WertegruppenElemente = np.append(self.WertegruppenElemente, WertegruppenElement(self.root, self.meinCanvas, self.posX1, self.posY1 + labelCounter*25, einMessobjekt, (eingabePosY2-eingabePosY1)/10))
            labelCounter = labelCounter + 1

    def setWertegruppeColorScheme(self, istTag):
        for einElement in self.WertegruppenElemente:
            einElement.setWertegruppenElementColorScheme(istTag)

    def update(self, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2):
        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2

        kandidat1x = (((self.posX2-self.posX1)-self.horizontalerAbstand)/8)
        kandidat1y = (((self.posY2-self.posY1) - self.vertikalerAbstand*self.anzahlWertegruppenElemente) / (self.anzahlWertegruppenElemente/(1*1.12)))
        kandidat1 = min(kandidat1x, kandidat1y)

        kandidat2x = (((self.posX2-self.posX1)/2-self.horizontalerAbstand)/8)
        kandidat2y = (((self.posY2-self.posY1) - self.vertikalerAbstand*(self.anzahlWertegruppenElemente/2)) / (self.anzahlWertegruppenElemente/(2*1.12)))
        kandidat2 = min(kandidat2x, kandidat2y)

        kandidat3x = (((self.posX2-self.posX1)/3-self.horizontalerAbstand)/8)
        kandidat3y = (((self.posY2-self.posY1) - self.vertikalerAbstand*(self.anzahlWertegruppenElemente/3)) / (self.anzahlWertegruppenElemente/(3*1.12)))
        kandidat3 = min(kandidat3x, kandidat3y)

        kandidat4x = (((self.posX2-self.posX1)/4-self.horizontalerAbstand)/8)
        kandidat4y = (((self.posY2-self.posY1) - self.vertikalerAbstand*(self.anzahlWertegruppenElemente/4)) / (self.anzahlWertegruppenElemente/(4*1.12)))
        kandidat4 = min(kandidat4x, kandidat4y)

        if (kandidat1 >= kandidat2) and (kandidat1 >= kandidat3) and (kandidat1 >= kandidat4):
            self.fontSize = fontSizeFaktor * kandidat1
            self.spaltenAnzahl = 1
        elif (kandidat2 >= kandidat1) and (kandidat2 >= kandidat3) and (kandidat2 >= kandidat4):
            self.fontSize = fontSizeFaktor * kandidat2
            self.spaltenAnzahl = 2
        elif (kandidat3 >= kandidat1) and (kandidat3 >= kandidat2) and (kandidat3 >= kandidat4):
            self.fontSize = fontSizeFaktor * kandidat3
            self.spaltenAnzahl = 3
        else:
            self.fontSize = fontSizeFaktor * kandidat4
            self.spaltenAnzahl = 4

        zusatz = 0.5                    # Da sonst die untersten Elemente mit den Rundinstrumenten kollidieren
        if self.spaltenAnzahl == 1:
            zusatz = 0                  # Darf aber nicht bei nur einer Spalte sein
        labelYcounter = 0
        labelXcounter = 0
        labelYanzahl = self.anzahlWertegruppenElemente/self.spaltenAnzahl
        for einElement in self.WertegruppenElemente:
            if self.posY1 + (labelYcounter + zusatz) * (self.fontSize*1.35 + self.vertikalerAbstand) >= self.posY2:
                labelYcounter = 0
                labelXcounter = labelXcounter + 1
            einElement.update(
                self.posX1 + labelXcounter * ( (self.posX2-self.posX1) / self.spaltenAnzahl + self.horizontalerAbstand),
                self.posY1 + labelYcounter * (self.fontSize*1.35 + self.vertikalerAbstand),
                self.fontSize
            )
            labelYcounter = labelYcounter + 1


    def delete(self):
        for einElement in self.WertegruppenElemente:
            einElement.delete()

    def zeichnen(self):
        for einElement in self.WertegruppenElemente:
            einElement.zeichnen()

    def updateAnzeige(self):
        for einElement in self.WertegruppenElemente:
            einElement.updateAnzeige()



class GraphenLinie:

    def __init__(self, eingabeCanvas, eingabeZugriffAufGraph, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeMessobjekt, eingabeGraphSamplingRate):
        self.meinCanvas = eingabeCanvas
        self.zugriffAufGraph = eingabeZugriffAufGraph

        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2

        self.meinMessobjekt = eingabeMessobjekt
        self.graphSamplingRate = eingabeGraphSamplingRate

        self.farbeGraphenLinie = None
        self.setColorScheme(True)

        self.data = np.array([])
        self.linien = np.array([])

    def updateAnzeige(self):

        kannObenWasWegstreichen = 1         # Ausgangslage: oben kann reingezoomt werden (ist 0 oder 1)
        kannUntenWasWegstreichen = 2        # Ausgangslage: unten kann reingezoomt werden (ist 0 oder 2)

        # Löschen des letzten Messwerts solange bis es ausreichend wenig Daten sind die dargestellt werden koennen
        while self.data.size * self.graphSamplingRate >= abs(self.posX2-self.posX1):
            self.data = np.delete(self.data, 0, axis=0)
        self.data = np.append(self.data, self.meinMessobjekt.value)

        # Alle alten Linien löschen
        for eineLinie in self.linien:
            self.meinCanvas.delete(int(eineLinie))
        self.linien = np.array([])

        if logg: print(self.posY2 - max(0, min((self.data.item(0) - self.meinMessobjekt.MinimalerYachsenWert) / (self.meinMessobjekt.MaximalerYachsenWert - self.meinMessobjekt.MinimalerYachsenWert) * (self.posY2-self.posY1), (self.posY2-self.posY1))), end = "")
        if logg: print(" ", end = "")
        if logg: print(self.data.item(0), end = "")
        if logg: print(" ", end = "")
        if logg: print(self.meinMessobjekt.MinimalerYachsenWert, end = "")
        if logg: print(" ", end = "")
        if logg: print(self.meinMessobjekt.MaximalerYachsenWert)

        for i in range(0, self.data.size-1):
            y1 = self.posY2 - max(0, min((self.data.item(i) - self.meinMessobjekt.MinimalerYachsenWert) / (self.meinMessobjekt.MaximalerYachsenWert - self.meinMessobjekt.MinimalerYachsenWert) * (self.posY2-self.posY1), (self.posY2-self.posY1)))


            if (y1 <= self.posY1*1.001):
                self.zugriffAufGraph.machObenPlatz()

            if (y1 >= self.posY2*0.999):
                self.zugriffAufGraph.machUntenPlatz()

            y2 = self.posY2 - max(0, min( (self.data.item(i+1) - self.meinMessobjekt.MinimalerYachsenWert) / (self.meinMessobjekt.MaximalerYachsenWert - self.meinMessobjekt.MinimalerYachsenWert) * (self.posY2-self.posY1), (self.posY2-self.posY1)))

            x1 = int(self.posX2 - (i  ) * self.graphSamplingRate)
            x2 = int(self.posX2 - (i+1) * self.graphSamplingRate)

            if (kannObenWasWegstreichen): #Soll nur überprüfen, wenn man noch was wegstreichen kann um Rechenaufwand zu minimieren
                if (y1-self.posY1 < 0.1*(self.posY2-self.posY1)) or (y2-self.posY1 < 0.1*(self.posY2-self.posY1)):
                    kannObenWasWegstreichen = 0
            if (kannUntenWasWegstreichen):
                if (self.posY2-y1 < 0.1*(self.posY2-self.posY1)) or (self.posY2-y2 < 0.1*(self.posY2-self.posY1)):
                    kannUntenWasWegstreichen = 0


            self.linien = np.append(self.linien, [self.meinCanvas.create_line(x1, y1, x2, y2, fill = self.farbeGraphenLinie, width= 2)])

        return kannObenWasWegstreichen+kannUntenWasWegstreichen

    def update(self, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeGraphSamplingRate):
        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2
        self.graphSamplingRate = eingabeGraphSamplingRate

    def delete(self):
        for eineLinie in self.linien:
            self.meinCanvas.delete(int(eineLinie))
        self.linien = np.array([])

    def setColorScheme(self, istTag):
        if istTag:
            self.farbeGraphenLinie = self.meinMessobjekt.istTagFarbe
        else:
            self.farbeGraphenLinie = self.meinMessobjekt.istNachtFarbe


class KoordinatenSystem:

    def __init__(self, eingabeCanvas, eingabeAbstandZumRand, eingabeKoordinatenSystemAchsenDicke,eingabeXachseAnfang,eingabeXachseEnde,eingabeYachseAnfang,eingabeYachseEnde, eingabeAchsenBeschriftungsText):

        self.meinCanvas = eingabeCanvas
        self.abstandZumRand = eingabeAbstandZumRand

        self.farbeKoordinatenSystemAchse = None

        self.koordinatenSystemAchsenDicke = eingabeKoordinatenSystemAchsenDicke
        self.xAchseAnfang = eingabeXachseAnfang
        self.xAchseEnde = eingabeXachseEnde
        self.yAchseAnfang = eingabeYachseAnfang
        self.yAchseEnde = eingabeYachseEnde

        self.dieXAchse = None
        self.dieYAchse = None

        self.achsenBeschriftungText = eingabeAchsenBeschriftungsText
        self.achsenBeschriftung = None
        self.achsenBeschriftungFarbe = None
        self.achsenBeschriftungFarbeBackground = None

        self.setKoordinatenSystemColorScheme(True)

    def setKoordinatenSystemColorScheme(self, istTag):
        if istTag:
            self.farbeKoordinatenSystemAchse = "grey10"
            self.achsenBeschriftungFarbe = "black"
            self.achsenBeschriftungFarbeBackground = "white"
        else:
            self.farbeKoordinatenSystemAchse = "grey90"
            self.achsenBeschriftungFarbe = "white"
            self.achsenBeschriftungFarbeBackground = "black"

    def zeichnen(self):
        self.dieXAchse = self.meinCanvas.create_line(self.xAchseAnfang, self.yAchseAnfang, self.xAchseEnde, self.yAchseAnfang, fill= self.farbeKoordinatenSystemAchse, width= self.koordinatenSystemAchsenDicke)
        self.dieYAchse = self.meinCanvas.create_line(self.xAchseAnfang, self.yAchseEnde, self.xAchseAnfang, self.yAchseAnfang, fill= self.farbeKoordinatenSystemAchse, width=self.koordinatenSystemAchsenDicke)
        self.achsenBeschriftung = self.meinCanvas.create_text(
            (
                self.xAchseAnfang,
                self.yAchseEnde
            ),
            anchor = "sw",
            text = self.achsenBeschriftungText,
            fill = self.achsenBeschriftungFarbe,
            font = ("Piboto", int(fontSizeFaktor*20))
        )

    # Update Funktion setzt nur die Werte neu und macht NIX grafisches!
    def update(self, eingabeXachseAnfang,eingabeXachseEnde,eingabeYachseAnfang,eingabeYachseEnde, eingabeAbstandZumRand):
        self.xAchseAnfang = eingabeXachseAnfang
        self.xAchseEnde = eingabeXachseEnde
        self.yAchseAnfang = eingabeYachseAnfang
        self.yAchseEnde = eingabeYachseEnde

        self.abstandZumRand = eingabeAbstandZumRand

    # Delete Funktion löscht nur die Linien, nicht das Objekt an sich!
    def delete(self):
        if(self.dieXAchse != None and self.dieYAchse != None):
            self.meinCanvas.delete(self.dieXAchse)
            self.meinCanvas.delete(self.dieYAchse)

        #self.achsenBeschriftung.destroy()
        self.meinCanvas.delete(self.achsenBeschriftung)

class Graph:

    def __init__(self, eingabeCanvas, eingabeAbstandZumRand, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeGraphenLegendenHoehe, eingabeMessobjekte, eingabeGraphHistorySize):
        self.Hilfsachsenbeschr = np.array([])

        self.meinCanvas = eingabeCanvas
        self.abstandZumRand = eingabeAbstandZumRand

        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2

        self.graphenLegendenHoehe = eingabeGraphenLegendenHoehe

        self.Messobjekte = eingabeMessobjekte
        self.MaximalerYachsenWert = 0
        self.MinimalerYachsenWert = 0

        self.graphHistorySize = eingabeGraphHistorySize
        self.graphSamplingRate = (self.posX2-self.posX1)/self.graphHistorySize

        self.linien = np.array([])
        self.anzahlAnGraphenLinien = 0
        for einMessobjekt in eingabeMessobjekte:
            self.linien = np.append(self.linien, GraphenLinie(
                self.meinCanvas,
                self,
                self.posX1,
                self.posX2,
                self.posY1 + self.graphenLegendenHoehe,
                self.posY2,
                einMessobjekt,
                self.graphSamplingRate
            ))
            self.anzahlAnGraphenLinien = self.anzahlAnGraphenLinien + 1
        self.yAchsenMinUndMaxBestimmen()

        self.koordinatenSystem = KoordinatenSystem(
            self.meinCanvas,
            self.abstandZumRand,
            1,
            self.posX1,
            self.posX2,
            self.posY2,
            self.posY1 + self.graphenLegendenHoehe,
            #self.Messobjekte[0].MesswertName + " (" + self.Messobjekte[0].MesswertEinheit + ")"
            self.Messobjekte[0].MesswertEinheit
            #self.koordinatenSystemBezeichnung
        )

        self.hilfslinien = Hilfslinien(
            self.meinCanvas,
            self.abstandZumRand,
            eingabePosX1,
            eingabePosX2,
            eingabePosY1 + self.graphenLegendenHoehe,
            eingabePosY2,
            self.MaximalerYachsenWert,
            self.MinimalerYachsenWert,
            1
        )

    def yAchsenMinUndMaxBestimmen(self):

        neuerMaximalerYachsenWert = -10000000000000
        neuerMinimalerYachsenWert = 10000000000000

        for eineGraphenLinie in self.linien:
            if eineGraphenLinie.meinMessobjekt.MaximalerYachsenWert > neuerMaximalerYachsenWert:
                neuerMaximalerYachsenWert = eineGraphenLinie.meinMessobjekt.MaximalerYachsenWert
            if eineGraphenLinie.meinMessobjekt.MinimalerYachsenWert < neuerMinimalerYachsenWert:
                neuerMinimalerYachsenWert = eineGraphenLinie.meinMessobjekt.MinimalerYachsenWert

        self.MaximalerYachsenWert = neuerMaximalerYachsenWert
        self.MinimalerYachsenWert = neuerMinimalerYachsenWert

    def setGraphColorScheme(self, istTag):
        self.hilfslinien.setHilfslinienColorScheme(istTag)

    # macht nur die Werte neu, ist NICHT fuers neu zeichnen zustaendig
    def update(self, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeAbstandZumRand, eingabeGraphHistorySize):

        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2

        self.abstandZumRand = eingabeAbstandZumRand

        self.graphHistorySize = eingabeGraphHistorySize
        self.graphSamplingRate = (self.posX2-self.posX1)/self.graphHistorySize

        self.hilfslinien.update(
            self.posX1,
            self.posX2,
            self.posY1 + self.graphenLegendenHoehe,
            self.posY2,
            self.MaximalerYachsenWert,
            self.MinimalerYachsenWert,
            self.abstandZumRand
        )

        self.koordinatenSystem.update(
            self.posX1,
            self.posX2,
            self.posY2,
            self.posY1 + self.graphenLegendenHoehe,
            self.abstandZumRand
        )

        for eineGraphenLinie in self.linien:
            eineGraphenLinie.update(self.posX1, self.posX2, self.posY1 + self.graphenLegendenHoehe, self.posY2, self.graphSamplingRate)

    def machObenPlatz(self):
        maxMinDifferenz = self.MaximalerYachsenWert - self.MinimalerYachsenWert

        for eineGraphenLinie in self.linien:
            eineGraphenLinie.meinMessobjekt.MaximalerYachsenWert = eineGraphenLinie.meinMessobjekt.MaximalerYachsenWert + 0.2*maxMinDifferenz

        self.yAchsenMinUndMaxBestimmen()

        self.hilfslinien.update(
            self.posX1,
            self.posX2,
            self.posY1 + self.graphenLegendenHoehe,
            self.posY2,
            self.MaximalerYachsenWert,
            self.MinimalerYachsenWert,
            self.abstandZumRand
        )

        self.hilfslinien.delete()
        self.hilfslinien.zeichnen()

    def machUntenPlatz(self):
        maxMinDifferenz = self.MaximalerYachsenWert - self.MinimalerYachsenWert

        for eineGraphenLinie in self.linien:
            eineGraphenLinie.meinMessobjekt.MinimalerYachsenWert = eineGraphenLinie.meinMessobjekt.MinimalerYachsenWert - 0.2*maxMinDifferenz

        self.yAchsenMinUndMaxBestimmen()

        self.hilfslinien.update(
            self.posX1,
            self.posX2,
            self.posY1 + self.graphenLegendenHoehe,
            self.posY2,
            self.MaximalerYachsenWert,
            self.MinimalerYachsenWert,
            self.abstandZumRand
        )

        self.hilfslinien.delete()
        self.hilfslinien.zeichnen()

    def updateAnzeige(self):

        kannBeiAllenObenWasWegstreichen = 0
        kannBeiAllenUntenWasWegstreichen = 0
        mussUpdaten = False

        for eineGraphenLinie in self.linien:
            returnValue = eineGraphenLinie.updateAnzeige()
            if (returnValue > 0):
                if (returnValue == 1) or (returnValue == 3):
                    kannBeiAllenObenWasWegstreichen = kannBeiAllenObenWasWegstreichen + 1
                if (returnValue == 2) or (returnValue == 3):
                    kannBeiAllenUntenWasWegstreichen = kannBeiAllenUntenWasWegstreichen + 1

        maxMinDifferenz = self.MaximalerYachsenWert - self.MinimalerYachsenWert

        if maxMinDifferenz > 9:

            if(self.linien.item(0).meinMessobjekt.MaximalerYachsenWert - 0.05*maxMinDifferenz > self.linien.item(0).meinMessobjekt.MinimalerYachsenWert + 0.05*maxMinDifferenz):
                if kannBeiAllenObenWasWegstreichen == self.anzahlAnGraphenLinien:
                    # Streich Oben was weg
                    mussUpdaten = True
                    for eineGraphenLinie in self.linien:
                        eineGraphenLinie.meinMessobjekt.MaximalerYachsenWert = eineGraphenLinie.meinMessobjekt.MaximalerYachsenWert - 0.05*maxMinDifferenz
                if kannBeiAllenUntenWasWegstreichen == self.anzahlAnGraphenLinien:
                    # Streich Unten was weg
                    mussUpdaten = True
                    for eineGraphenLinie in self.linien:
                        eineGraphenLinie.meinMessobjekt.MinimalerYachsenWert = eineGraphenLinie.meinMessobjekt.MinimalerYachsenWert + 0.05*maxMinDifferenz

        if mussUpdaten:

            self.yAchsenMinUndMaxBestimmen()

            self.hilfslinien.update(
                self.posX1,
                self.posX2,
                self.posY1 + self.graphenLegendenHoehe,
                self.posY2,
                self.MaximalerYachsenWert,
                self.MinimalerYachsenWert,
                self.abstandZumRand
            )

            self.hilfslinien.delete()
            self.hilfslinien.zeichnen()

    def delete(self):
        self.hilfslinien.delete()
        self.koordinatenSystem.delete()

        for eineGraphenLinie in self.linien:
            eineGraphenLinie.delete()

    def zeichnen(self):
        self.koordinatenSystem.zeichnen()
        self.hilfslinien.zeichnen()

    def setColorScheme(self, istTag):
        self.koordinatenSystem.setKoordinatenSystemColorScheme(istTag)
        self.hilfslinien.setHilfslinienColorScheme(istTag)
        for eineGraphenLinie in self.linien:
            eineGraphenLinie.setColorScheme(istTag)


class Dock:

    def __init__(self, eingabeRoot, eingabeApp, eingabeCanvas, eingabeDockHoehe, eingabeAbstandZumRand):
        self.root = eingabeRoot
        self.zugriffAufApp = eingabeApp
        self.meinCanvas = eingabeCanvas

        self.dockHoehe = eingabeDockHoehe
        self.abstandZumRand = eingabeAbstandZumRand

        self.dockX1 = self.abstandZumRand
        self.dockX2 = self.meinCanvas.winfo_width() - self.abstandZumRand
        self.dockY1 = self.meinCanvas.winfo_height() - self.dockHoehe - self.abstandZumRand
        self.dockY2 = self.meinCanvas.winfo_height() - self.abstandZumRand

        self.update(eingabeDockHoehe, eingabeAbstandZumRand)

        # Farben
        self.farbeDockBackground = None
        self.farbeDockLabelBackground = None
        self.farbeDockLabelForeground = None
        self.farbeDockTaste = None
        self.farbeDockEingabeBackground = None
        self.farbeDockEingabeForeground = None
        self.setColorScheme(True)

        self.dockFont = "Piboto"
        self.dockFontSize = int(self.dockHoehe/2*fontSizeFaktor)

        self.dockFrame = Frame(self.root)
        self.dockFrame.pack()

        self.dockValues = None
        self.schiebeRegler = None
        self.tastenLabels = None

        self.letztesHorizontaleTeilungValue = 0
        self.letztesVertikaleTeilungValue = 0

        self.wUserFehlerfeld = None

        self.Testbeschreibung = ""

        # Da das Dock relativ kurz nach Programmstart erstellt wird kann man auch die Erstellzeit vom Dock verwenden
        self.startZeitText = str(time.strftime("%H:%M:%S", time.localtime(time.time())))

        self.menuPunkte = ["Zurück", "Kalibrieren", "Einheit Schub", "Glättung", "Horizontale Teilung", "Vertikale Teilung", "Tag/Nacht Wechsel", "Benutzer wechseln", "Testbeschreibung eingeben"]
        self.menuCanvas = None
        self.aktivesMenu = False

        self.userAnmeldungCanvas = None
        self.aktiveAnmeldung = False

        self.kalibrationsCanvas = None
        self.aktiverKalibrierungsvorgang = False
        self.aktiverKalibrierungsvorgangFortsetzung = False

        self.glaettungsCanvas = None
        self.aktiveGlaettungsAenderung = False

        self.horizontaleTeilungCanvas = None
        self.aktiveAenderungHorizontaleTeilung = False

        self.vertikaleTeilungCanvas = None
        self.aktiveAenderungVertikaleTeilung = False

        self.benutzerStringVar = StringVar()
        self.benutzerStringVar.set("Benutzer: " + self.zugriffAufApp.userName)

        self.testbeschreibungEingebenCanvas = None
        self.aktiveTestbeschreibungEingeben = False
        
    def setColorScheme(self, istTag):
        if istTag:
            self.farbeDockBackground = "#E9E9E9"
            self.farbeDockLabelBackground = "grey60"
            self.farbeDockLabelForeground = "grey30"
            self.farbeDockTaste = "#2F6ADE"
            self.farbeDockEingabeBackground = "grey60"
            self.farbeDockEingabeForeground = "black"
            self.farbeDockCanvasesBackground = "white"
            self.farbeDockCanvasesForeground = "black"

        else:
            self.farbeDockBackground = "#212121"
            self.farbeDockLabelBackground = "grey30"
            self.farbeDockLabelForeground = "grey60"
            self.farbeDockTaste = "#2F6ADE"
            self.farbeDockEingabeBackground = "grey30"
            self.farbeDockEingabeForeground = "grey60"
            self.farbeDockCanvasesBackground = "#0a0a0a"
            self.farbeDockCanvasesForeground = "white"

    def zeichnen(self):

        if (self.aktiveAenderungHorizontaleTeilung == False) & (self.aktiveAenderungVertikaleTeilung == False):

            self.dockRechteck = self.meinCanvas.create_rectangle(self.dockX1, self.dockY1, self.dockX2, self.dockY2, fill = self.farbeDockBackground, width = 3, outline="#9a9a9a")
            self.dockRechteck2 = self.meinCanvas.create_rectangle(self.dockX1, self.dockY1, self.dockX2-1, self.dockY2-1, fill = self.farbeDockBackground, width = 0)

            self.dockValues = {
                "Sampling" : Label(
                    self.root,
                    text="Sampling",
                    bg=self.farbeDockBackground,
                    fg=self.farbeDockLabelForeground,
                    font = (self.dockFont, int(fontSizeFaktor*self.dockFontSize))
                ),
                "Start" : Label(
                    self.root,
                    text="Start: " + self.startZeitText,
                    bg=self.farbeDockBackground,
                    fg=self.farbeDockLabelForeground,
                    font = (self.dockFont, int(fontSizeFaktor*self.dockFontSize*0.8))
                ),
                "Benutzer" : Label(
                    self.root,
                    textvariable=self.benutzerStringVar,
                    bg=self.farbeDockBackground,
                    fg=self.farbeDockLabelForeground,
                    font = (self.dockFont, int(fontSizeFaktor*self.dockFontSize*0.8))
                ),
                "GlättungsLabel" : Label(
                    self.root,
                    text="Glättung: " + str(self.zugriffAufApp.Glättung),
                    bg=self.farbeDockBackground,
                    fg=self.farbeDockLabelForeground,
                    font = (self.dockFont, int(fontSizeFaktor*self.dockFontSize*0.8))
                ),
                "TestbeschreibungsLabel" : Label(
                    self.root,
                    text="Aktuelle Testbeschreibung: ",
                    bg=self.farbeDockBackground,
                    fg=self.farbeDockLabelForeground,
                    font = (self.dockFont, int(fontSizeFaktor*self.dockFontSize*0.8))
                ),
                "TestbeschreibungsWert" : Label(
                    self.root,
                    text=str(self.Testbeschreibung),
                    bg=self.farbeDockBackground,
                    fg=self.farbeDockLabelForeground,
                    font = (self.dockFont, int(fontSizeFaktor*self.dockFontSize*0.7))
                ),
            }

            for key in self.dockValues:
                self.dockValues[key].pack()

            # Neue Positionierung der dockValues
            self.dockValues["Sampling"].place(          x = self.dockX1 + self.abstandZumRand + 275 ,       y = self.dockY1 + self.dockHoehe * 0.4,  anchor = "e")
            self.dockValues["Start"].place(             x = self.dockX1 + self.abstandZumRand + 325,        y = self.dockY1 + self.dockHoehe * 0.34, anchor = "sw")
            self.dockValues["Benutzer"].place(          x = self.dockX1 + self.abstandZumRand + 325,        y = self.dockY1 + self.dockHoehe * 0.66, anchor = "sw")
            self.dockValues["GlättungsLabel"].place(    x = self.dockX1 + self.abstandZumRand + 325,        y = self.dockY1 + self.dockHoehe * 0.98, anchor = "sw")
#            self.dockValues["TestbeschreibungsLabel"].place(    x = self.dockX1 + self.abstandZumRand + 950,   y = self.dockY1 + self.dockHoehe * 0.5, anchor = "sw")
            self.dockValues["TestbeschreibungsLabel"].place(    x = self.dockX2 - 480,   y = self.dockY1 + self.dockHoehe * 0.5, anchor = "sw")
            self.dockValues["TestbeschreibungsWert"].place(     x = self.dockX2 - 480,   y = self.dockY1 + self.dockHoehe * 0.75, anchor = "sw")

            self.tastenLabels = {
                "1": Label(
                        self.root,
                        text = " 1 ",
                        bg = self.farbeDockTaste,
                        fg = "white",
                        font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
                ),
                "2": Label(
                        self.root,
                        text = " 2 ",
                        bg = self.farbeDockTaste,
                        fg = "white",
                        font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
                ),
                "Menu": Label(
                        self.root,
                        text = "Menu",
                        bg = self.farbeDockBackground,
                        fg = self.farbeDockTaste,
                        font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
                ),
                "SShot": Label(
                        self.root,
                        text = "ScreenShot",
                        bg = self.farbeDockBackground,
                        fg = self.farbeDockTaste,
                        font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
                )
            }

            for key in self.tastenLabels:
                self.tastenLabels[key].pack()

            self.tastenLabels["1"].place(
                x = self.dockX1 + self.abstandZumRand + 750,
                y = self.dockY1+self.dockHoehe*0.35,
                anchor="c"
            )
            self.tastenLabels["2"].place(
                x = self.dockX1 + self.abstandZumRand + 850,
                y = self.dockY1+self.dockHoehe*0.35,
                anchor="c"
            )
            self.tastenLabels["Menu"].place(
                x = self.dockX1 + self.abstandZumRand + 750,
                y = self.dockY1+self.dockHoehe*0.75,
                anchor="c"
            )
            self.tastenLabels["SShot"].place(
                x = self.dockX1 + self.abstandZumRand + 850,
                y = self.dockY1+self.dockHoehe*0.75,
                anchor="c"
            )


    def delete(self):
        self.meinCanvas.delete(self.dockRechteck)
        self.meinCanvas.delete(self.dockRechteck2)

        for key in self.dockValues:
            self.dockValues[key].destroy()
        for key in self.tastenLabels:
            self.tastenLabels[key].destroy()

    def updateSamplingAnzeige(self, eingabeSamplingRate):
        self.dockValues["Sampling"].config(text = '{:1.1f}'.format(eingabeSamplingRate) + " Sample/sec")

    def update(self, eingabeDockHoehe, eingabeAbstandZumRand):
        self.dockHoehe = eingabeDockHoehe
        self.dockX1 = eingabeAbstandZumRand
        self.dockX2 = self.meinCanvas.winfo_width() - eingabeAbstandZumRand
        self.dockY1 = self.meinCanvas.winfo_height() - self.dockHoehe - eingabeAbstandZumRand
        self.dockY2 = self.meinCanvas.winfo_height() - eingabeAbstandZumRand
        self.dockFontSize = int(self.dockHoehe/2*fontSizeFaktor)

    def horizontalerSchiebereglerCommand(self, value):
        if value != self.letztesHorizontaleTeilungValue:
            self.zugriffAufApp.fensterBreiteAufteilungWertegruppenRundinstrumente = int(value)
            self.letztesHorizontaleTeilungValue = value
            self.zugriffAufApp.guiReset()

    def vertikalerSchiebereglerCommand(self, value):
        if value != self.letztesVertikaleTeilungValue:
            self.zugriffAufApp.fensterHoeheAufteilungWertegruppenRundinstrumente = int(value)
            self.letztesVertikaleTeilungValue = value
            self.zugriffAufApp.guiReset()

    def shutdownCommand(self):
        command = "/usr/bin/sudo /sbin/shutdown now"
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output = process.communicate()[0]
        print(output)

    def restartCommand(self, eingabeUserName = "login"):
        os.execv(sys.executable, ['python3.6'] + [sys.argv[0]] + [eingabeUserName])


    def menuFensterNachUnten(self):
        if self.menuCanvas != None:
            self.menuLabelArray[self.ausgewaehlterMenuIndex].config(bg = self.farbeDockCanvasesBackground, fg=self.farbeDockCanvasesForeground)

            self.ausgewaehlterMenuIndex = self.ausgewaehlterMenuIndex + 1
            if(self.ausgewaehlterMenuIndex == self.menuLabelCounter):
                self.ausgewaehlterMenuIndex = 0

            self.menuLabelArray[self.ausgewaehlterMenuIndex].config(bg = "#2F6ADE", fg="white")
        else:
            print("Kein aktives Menu")

    def menuFensterNachOben(self):
        if self.menuCanvas != None:
            self.menuLabelArray[self.ausgewaehlterMenuIndex].config(bg = self.farbeDockCanvasesBackground, fg=self.farbeDockCanvasesForeground)

            self.ausgewaehlterMenuIndex = self.ausgewaehlterMenuIndex - 1
            if(self.ausgewaehlterMenuIndex == -1):
                self.ausgewaehlterMenuIndex = self.menuLabelCounter -1

            self.menuLabelArray[self.ausgewaehlterMenuIndex].config(bg = "#2F6ADE", fg="white")
        else:
            print("Kein aktives Menu")

    def menuFensterAufbau(self):
        self.aktivesMenu = True

        self.menuCanvas = Canvas(self.root, width=self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterBreite"]-2*self.abstandZumRand, height=self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterHoehe"]-2*self.abstandZumRand, bg = self.farbeDockCanvasesBackground)
        self.menuCanvas.place(x = self.abstandZumRand, y = self.abstandZumRand, anchor="nw")

        self.menuLabelArray = np.array([])

        self.ausgewaehlterMenuIndex = 0

        self.menuLabelCounter = 0
        for punkt in self.menuPunkte:
            self.menuLabelArray = np.append(self.menuLabelArray, [Label(
                self.menuCanvas,
                bg = self.farbeDockCanvasesBackground,
                fg = self.farbeDockCanvasesForeground,
                text = punkt,
                font = ("Piboto", int(fontSizeFaktor*18))
            )])
            self.menuLabelArray[self.menuLabelCounter].place(
                x = self.abstandZumRand * 2,
                y = self.abstandZumRand * 4 + int(fontSizeFaktor * 18 + 15) * self.menuLabelCounter
            )
            self.menuLabelCounter = self.menuLabelCounter + 1
        self.menuLabelArray[self.ausgewaehlterMenuIndex].config(bg = "#2F6ADE", fg="white")

        self.menuTastenLabels = {
            "1": Label(
                self.menuCanvas,
                text = " 1 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "2": Label(
                self.menuCanvas,
                text = " 2 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "3": Label(
                self.menuCanvas,
                text = " 3 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "Rauf": Label(
                self.menuCanvas,
                text = "Up",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Runter": Label(
                self.menuCanvas,
                text = "Down",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Auswaehlen": Label(
                self.menuCanvas,
                text = " Enter",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            )
        }

        self.menuTastenLabels["1"].place(
            x = self.meinCanvas.winfo_width()/2 - 60,
            y = self.dockY1+self.dockHoehe*0.3,
            anchor="c"
        )
        self.menuTastenLabels["2"].place(
            x = self.meinCanvas.winfo_width()/2,
            y = self.dockY1+self.dockHoehe*0.3,
            anchor="c"
        )
        self.menuTastenLabels["3"].place(
            x = self.meinCanvas.winfo_width()/2 + 60,
            y = self.dockY1+self.dockHoehe*0.3,
            anchor="c"
        )
        self.menuTastenLabels["Rauf"].place(
            x = self.meinCanvas.winfo_width()/2 - 60,
            y = self.dockY1+self.dockHoehe*0.7,
            anchor="c"
        )
        self.menuTastenLabels["Runter"].place(
            x = self.meinCanvas.winfo_width()/2,
            y = self.dockY1+self.dockHoehe*0.7,
            anchor="c"
        )
        self.menuTastenLabels["Auswaehlen"].place(
            x = self.meinCanvas.winfo_width()/2 + 60,
            y = self.dockY1+self.dockHoehe*0.7,
            anchor="c"
        )

        self.root.update()

    def menuFortsetzung(self):
        #["Zurück", "Kalibrieren", "Einheit Schub", "Glättung", "Tag/Nacht Wechsel", "Benutzer wechseln"]
        self.menuDelete()
        if self.menuPunkte[self.ausgewaehlterMenuIndex] == "Kalibrieren":
            self.kalibrieren()

        elif self.menuPunkte[self.ausgewaehlterMenuIndex] == "Einheit Schub":
            print("Einheit Schub")

        elif self.menuPunkte[self.ausgewaehlterMenuIndex] == "Glättung":
            self.glaettungsFensterAufbau()

        elif self.menuPunkte[self.ausgewaehlterMenuIndex] == "Horizontale Teilung":
            self.horizontaleTeilungFensterAufbau()

        elif self.menuPunkte[self.ausgewaehlterMenuIndex] == "Vertikale Teilung":
            self.vertikaleTeilungFensterAufbau()

        elif self.menuPunkte[self.ausgewaehlterMenuIndex] == "Tag/Nacht Wechsel":
            self.zugriffAufApp.toggleColorScheme()

        elif self.menuPunkte[self.ausgewaehlterMenuIndex] == "Benutzer wechseln":
            self.userAnmeldung()

        elif self.menuPunkte[self.ausgewaehlterMenuIndex] == "Testbeschreibung eingeben":
            self.testbeschreibungEingeben()

        else:
            print("Zurück")

    def menuDelete(self):
        if self.aktivesMenu:
            self.menuCanvas.destroy()
            self.menuTastenLabels = None
        else:
            print("Kein aktives Menu")
        self.menuLabelArray = None
        self.menuLabelCounter = 0
        self.aktivesMenu = False


    def horizontaleTeilungNachLinks(self):
        if self.zugriffAufApp.fensterBreiteAufteilungWertegruppenRundinstrumente > 10:
            self.zugriffAufApp.fensterBreiteAufteilungWertegruppenRundinstrumente -= 1
            self.zugriffAufApp.guiReset()
            self.horizontaleTeilungCanvas.destroy()
            self.root.update()
            self.horizontaleTeilungFensterZeichnen()

    def horizontaleTeilungNachRechts(self):
        if self.zugriffAufApp.fensterBreiteAufteilungWertegruppenRundinstrumente < 90:
            self.zugriffAufApp.fensterBreiteAufteilungWertegruppenRundinstrumente += 1
            self.zugriffAufApp.guiReset()
            self.horizontaleTeilungCanvas.destroy()
            self.root.update()
            self.horizontaleTeilungFensterZeichnen()

    def horizontaleTeilungFensterAbbruch(self):
        self.zugriffAufApp.fensterBreiteAufteilungWertegruppenRundinstrumente = self.horizontaleTeilungBackup
        self.horizontaleTeilungFensterDelete()

    def horizontaleTeilungFensterDelete(self):
        if self.aktiveAenderungHorizontaleTeilung:
            self.horizontaleTeilungCanvas.destroy()
        self.aktiveAenderungHorizontaleTeilung = False
        self.horizontaleTeilungCanvas = None
        self.zugriffAufApp.guiReset()

    def horizontaleTeilungFensterZeichnen(self):
        self.horizontaleTeilungCanvas = Canvas(
            self.root,
            width = self.dockX2-self.dockX1,
            height = self.dockY2-self.dockY1,
            bg = self.farbeDockCanvasesBackground
        )
        self.horizontaleTeilungCanvas.place(x = self.dockX1, y = self.dockY1, anchor = "nw")

        self.horizontaleTeilungLabels = {
            "1": Label(
                self.horizontaleTeilungCanvas,
                text = " 1 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "2": Label(
                self.horizontaleTeilungCanvas,
                text = " 2 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "3": Label(
                self.horizontaleTeilungCanvas,
                text = " 3 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "4": Label(
                self.horizontaleTeilungCanvas,
                text = " 4 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "Rauf": Label(
                self.horizontaleTeilungCanvas,
                text = "Links",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Runter": Label(
                self.horizontaleTeilungCanvas,
                text = "Rechts",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Auswaehlen": Label(
                self.horizontaleTeilungCanvas,
                text = " Enter",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Abbrechen": Label(
                self.horizontaleTeilungCanvas,
                text = " Abbrechen",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            )
        }

        self.horizontaleTeilungLabels["1"].place(
            x = (self.dockX2-self.dockX1)/2 - 150,
            y = (self.dockY2-self.dockY1)*0.35,
            anchor="c"
        )
        self.horizontaleTeilungLabels["2"].place(
            x = (self.dockX2-self.dockX1)/2 - 50,
            y = (self.dockY2-self.dockY1)*0.35,
            anchor="c"
        )
        self.horizontaleTeilungLabels["3"].place(
            x = (self.dockX2-self.dockX1)/2 + 50,
            y = (self.dockY2-self.dockY1)*0.35,
            anchor="c"
        )
        self.horizontaleTeilungLabels["4"].place(
            x = (self.dockX2-self.dockX1)/2 + 150,
            y = (self.dockY2-self.dockY1)*0.35,
            anchor="c"
        )
        self.horizontaleTeilungLabels["Rauf"].place(
            x = (self.dockX2-self.dockX1)/2 - 150,
            y = (self.dockY2-self.dockY1)*0.75,
            anchor="c"
        )
        self.horizontaleTeilungLabels["Runter"].place(
            x = (self.dockX2-self.dockX1)/2 - 50,
            y = (self.dockY2-self.dockY1)*0.75,
            anchor="c"
        )
        self.horizontaleTeilungLabels["Auswaehlen"].place(
            x = (self.dockX2-self.dockX1)/2 + 50,
            y = (self.dockY2-self.dockY1)*0.75,
            anchor="c"
        )
        self.horizontaleTeilungLabels["Abbrechen"].place(
            x = (self.dockX2-self.dockX1)/2 + 150,
            y = (self.dockY2-self.dockY1)*0.75,
            anchor="c"
        )

        self.root.update()

    def horizontaleTeilungFensterAufbau(self):
        self.horizontaleTeilungBackup = self.zugriffAufApp.fensterBreiteAufteilungWertegruppenRundinstrumente
        self.aktiveAenderungHorizontaleTeilung = True
        self.horizontaleTeilungFensterZeichnen()


    def vertikaleTeilungNachLinks(self):
#        if self.zugriffAufApp.fensterHoeheAufteilungWertegruppenRundinstrumente > 30:   ... SP Aenderung damit Wertegruppen kleiner werden koennen
        if self.zugriffAufApp.fensterHoeheAufteilungWertegruppenRundinstrumente > 15:
            self.zugriffAufApp.fensterHoeheAufteilungWertegruppenRundinstrumente -= 1
            self.zugriffAufApp.guiReset()
            self.vertikaleTeilungCanvas.destroy()
            self.root.update()
            self.vertikaleTeilungFensterZeichnen()

    def vertikaleTeilungNachRechts(self):
        if self.zugriffAufApp.fensterHoeheAufteilungWertegruppenRundinstrumente < 70:
            self.zugriffAufApp.fensterHoeheAufteilungWertegruppenRundinstrumente += 1
            self.zugriffAufApp.guiReset()
            self.vertikaleTeilungCanvas.destroy()
            self.root.update()
            self.vertikaleTeilungFensterZeichnen()

    def vertikaleTeilungFensterAbbruch(self):
        self.zugriffAufApp.fensterHoeheAufteilungWertegruppenRundinstrumente = self.vertikaleTeilungBackup
        self.vertikaleTeilungFensterDelete()

    def vertikaleTeilungFensterDelete(self):
        if self.aktiveAenderungVertikaleTeilung:
            self.vertikaleTeilungCanvas.destroy()
        self.aktiveAenderungVertikaleTeilung = False
        self.vertikaleTeilungCanvas = None
        self.zugriffAufApp.guiReset()

    def vertikaleTeilungFensterZeichnen(self):
        self.vertikaleTeilungCanvas = Canvas(
            self.root,
            width = self.dockX2-self.dockX1,
            height = self.dockY2-self.dockY1,
            bg = self.farbeDockCanvasesBackground
        )
        self.vertikaleTeilungCanvas.place(x = self.dockX1, y = self.dockY1, anchor = "nw")

        self.vertikaleTeilungLabels = {
            "1": Label(
                self.vertikaleTeilungCanvas,
                text = " 1 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "2": Label(
                self.vertikaleTeilungCanvas,
                text = " 2 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "3": Label(
                self.vertikaleTeilungCanvas,
                text = " 3 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "4": Label(
                self.vertikaleTeilungCanvas,
                text = " 4 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "Rauf": Label(
                self.vertikaleTeilungCanvas,
                text = "Rauf",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Runter": Label(
                self.vertikaleTeilungCanvas,
                text = "Runter",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Auswaehlen": Label(
                self.vertikaleTeilungCanvas,
                text = " Enter",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Abbrechen": Label(
                self.vertikaleTeilungCanvas,
                text = " Abbrechen",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            )
        }

        self.vertikaleTeilungLabels["1"].place(
            x = (self.dockX2-self.dockX1)/2 - 150,
            y = (self.dockY2-self.dockY1)*0.35,
            anchor="c"
        )
        self.vertikaleTeilungLabels["2"].place(
            x = (self.dockX2-self.dockX1)/2 - 50,
            y = (self.dockY2-self.dockY1)*0.35,
            anchor="c"
        )
        self.vertikaleTeilungLabels["3"].place(
            x = (self.dockX2-self.dockX1)/2 + 50,
            y = (self.dockY2-self.dockY1)*0.35,
            anchor="c"
        )
        self.vertikaleTeilungLabels["4"].place(
            x = (self.dockX2-self.dockX1)/2 + 150,
            y = (self.dockY2-self.dockY1)*0.35,
            anchor="c"
        )
        self.vertikaleTeilungLabels["Rauf"].place(
            x = (self.dockX2-self.dockX1)/2 - 150,
            y = (self.dockY2-self.dockY1)*0.75,
            anchor="c"
        )
        self.vertikaleTeilungLabels["Runter"].place(
            x = (self.dockX2-self.dockX1)/2 - 50,
            y = (self.dockY2-self.dockY1)*0.75,
            anchor="c"
        )
        self.vertikaleTeilungLabels["Auswaehlen"].place(
            x = (self.dockX2-self.dockX1)/2 + 50,
            y = (self.dockY2-self.dockY1)*0.75,
            anchor="c"
        )
        self.vertikaleTeilungLabels["Abbrechen"].place(
            x = (self.dockX2-self.dockX1)/2 + 150,
            y = (self.dockY2-self.dockY1)*0.75,
            anchor="c"
        )

        self.root.update()

    def vertikaleTeilungFensterAufbau(self):
        self.vertikaleTeilungBackup = self.zugriffAufApp.fensterHoeheAufteilungWertegruppenRundinstrumente
        self.aktiveAenderungVertikaleTeilung = True
        self.vertikaleTeilungFensterZeichnen()


    def glaettungsFensterRauf(self):
        if self.zugriffAufApp.Glättung < 20:
            self.zugriffAufApp.Glättung += 1
            self.anzeigeLabelAktuelleGlaettung.config(text = "Glättung: " + str(self.zugriffAufApp.Glättung))

    def glaettungsFensterRunter(self):
        if self.zugriffAufApp.Glättung > 0:
            self.zugriffAufApp.Glättung -= 1
            self.anzeigeLabelAktuelleGlaettung.config(text = "Glättung: " + str(self.zugriffAufApp.Glättung))

    def glaettungsFensterDelete(self):
        if self.aktiveGlaettungsAenderung:
            self.glaettungsCanvas.destroy()
            self.glaettungTastenLabels = None
        self.aktiveGlaettungsAenderung = False

    def glaettungsAenderungAbbruch(self):
        if self.aktiveGlaettungsAenderung:
            self.zugriffAufApp.Glättung = self.glaettungsBackup
            self.glaettungsFensterDelete()

    def glaettungsFensterFortsetzung(self):
        if self.aktiveGlaettungsAenderung:
            self.dockValues["GlättungsLabel"].config(text = "Glättung: " + str(self.zugriffAufApp.Glättung))
            for einMessobjektKey in self.zugriffAufApp.MesswertObjekte:
                self.zugriffAufApp.MesswertObjekte[einMessobjektKey].updateGlaettung(self.zugriffAufApp.Glättung)
            self.glaettungsFensterDelete()
            self.zugriffAufApp.guiReset()

    def glaettungsFensterAufbau(self):
        self.aktiveGlaettungsAenderung = True
        self.glaettungsBackup = self.zugriffAufApp.Glättung

        self.glaettungsCanvas = Canvas(
            self.root,
            width = self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterBreite"],
            height = self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterHoehe"],
            bg = self.farbeDockCanvasesBackground
        )
        self.glaettungsCanvas.place(x = 0, y = 0, anchor = "nw")

        self.anzeigeLabelAktuelleGlaettung = Label(
            self.glaettungsCanvas,
            text = "Glättung: " + str(self.zugriffAufApp.Glättung),
            bg = self.farbeDockCanvasesBackground,
            fg = self.farbeDockCanvasesForeground,
            font = ("Piboto", int(fontSizeFaktor*40))
        )

        self.anzeigeLabelAktuelleGlaettung.place(x = self.meinCanvas.winfo_width()/2, y = self.meinCanvas.winfo_height()/2, anchor = "s")

        self.glaettungTastenLabels = {
            "1": Label(
                self.glaettungsCanvas,
                text = " 1 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "2": Label(
                self.glaettungsCanvas,
                text = " 2 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "3": Label(
                self.glaettungsCanvas,
                text = " 3 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "4": Label(
                self.glaettungsCanvas,
                text = " 4 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "Rauf": Label(
                self.glaettungsCanvas,
                text = " Up ",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Runter": Label(
                self.glaettungsCanvas,
                text = " Down ",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Auswaehlen": Label(
                self.glaettungsCanvas,
                text = " Enter",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Abbrechen": Label(
                self.glaettungsCanvas,
                text = " Abbrechen",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            )
        }

        self.glaettungTastenLabels["1"].place(
            x = self.meinCanvas.winfo_width()/2 - 150,
            y = self.dockY1+self.dockHoehe*0.35,
            anchor="c"
        )
        self.glaettungTastenLabels["2"].place(
            x = self.meinCanvas.winfo_width()/2 - 50,
            y = self.dockY1+self.dockHoehe*0.35,
            anchor="c"
        )
        self.glaettungTastenLabels["3"].place(
            x = self.meinCanvas.winfo_width()/2 + 50,
            y = self.dockY1+self.dockHoehe*0.35,
            anchor="c"
        )
        self.glaettungTastenLabels["4"].place(
            x = self.meinCanvas.winfo_width()/2 + 150,
            y = self.dockY1+self.dockHoehe*0.35,
            anchor="c"
        )
        self.glaettungTastenLabels["Rauf"].place(
            x = self.meinCanvas.winfo_width()/2 - 150,
            y = self.dockY1+self.dockHoehe*0.75,
            anchor="c"
        )
        self.glaettungTastenLabels["Runter"].place(
            x = self.meinCanvas.winfo_width()/2 - 50,
            y = self.dockY1+self.dockHoehe*0.75,
            anchor="c"
        )
        self.glaettungTastenLabels["Auswaehlen"].place(
            x = self.meinCanvas.winfo_width()/2 + 50,
            y = self.dockY1+self.dockHoehe*0.75,
            anchor="c"
        )
        self.glaettungTastenLabels["Abbrechen"].place(
            x = self.meinCanvas.winfo_width()/2 + 150,
            y = self.dockY1+self.dockHoehe*0.75,
            anchor="c"
        )

        self.root.update()


    def kalibrieren(self):
        self.aktiverKalibrierungsvorgang = True

        self.kalibrationsCanvas = Canvas(
            self.root,
            width = self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterBreite"],
            height = self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterHoehe"],
            bg = self.farbeDockCanvasesBackground
        )
        self.kalibrationsCanvas.place(x = 0, y = 0, anchor = "nw")

        self.bisherigeKalibrationswerte = self.kalibrationsCanvas.create_text(
            (
                self.meinCanvas.winfo_width()/2,
                self.meinCanvas.winfo_height()/2 - 50
            ),
            text = "Bisherige Kalibrationswerte: " + str(self.zugriffAufApp.meinConfigHandler.modocKonstanten["drehmoment_kal"]) + " bzw " + str(self.zugriffAufApp.meinConfigHandler.modocKonstanten["schub_kal"]),
            anchor = "s",
            fill = self.farbeDockCanvasesForeground,
            font = ("Piboto", int(fontSizeFaktor*36))
        )

        self.frage = self.kalibrationsCanvas.create_text(
            (
                self.meinCanvas.winfo_width()/2,
                self.meinCanvas.winfo_height()/2
            ),
            text = "Sensoren für Drehmoment und Schub kalibrieren?",
            anchor = "s",
            fill = self.farbeDockCanvasesForeground,
            font = ("Piboto", int(fontSizeFaktor*36))
        )

        self.kalbirationsTastenLabels = {
             "1": Label(
                self.kalibrationsCanvas,
                text = " 1 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "4": Label(
                self.kalibrationsCanvas,
                text = " 4 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "Jetzt kalibrieren": Label(
                self.kalibrationsCanvas,
                text = "Jetzt kalibrieren",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Abbrechen": Label(
                self.kalibrationsCanvas,
                text = " Abbrechen",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            )
        }

        self.kalbirationsTastenLabels["1"].place(
            x = self.meinCanvas.winfo_width()/2 - 50,
            y = self.dockY1+self.dockHoehe*0.3,
            anchor="c"
        )
        self.kalbirationsTastenLabels["4"].place(
            x = self.meinCanvas.winfo_width()/2 + 50,
            y = self.dockY1+self.dockHoehe*0.3,
            anchor="c"
        )
        self.kalbirationsTastenLabels["Jetzt kalibrieren"].place(
            x = self.meinCanvas.winfo_width()/2 - 50,
            y = self.dockY1+self.dockHoehe*0.7,
            anchor="c"
        )
        self.kalbirationsTastenLabels["Abbrechen"].place(
            x = self.meinCanvas.winfo_width()/2 + 50,
            y = self.dockY1+self.dockHoehe*0.7,
            anchor="c"
        )

        self.root.update()


    def kalibrierenEnde(self):
        if self.aktiverKalibrierungsvorgang or self.aktiverKalibrierungsvorgangFortsetzung:
            self.kalibrationsCanvas.destroy()
        self.aktiverKalibrierungsvorgang = False
        self.aktiverKalibrierungsvorgangFortsetzung = False
        self.kalbirationsTastenLabels = None


    def eigentlicheKalibrieren(self):
        self.kalibrierenEnde()
        self.aktiverKalibrierungsvorgangFortsetzung = True

        self.kalibrationsCanvas = Canvas(
            self.root,
            width = self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterBreite"],
            height = self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterHoehe"],
            bg = self.farbeDockCanvasesBackground
        )
        self.kalibrationsCanvas.place(x = 0, y = 0, anchor = "nw")

        self.anzeigeKalibrierungsErgebnisse = Label(
            self.kalibrationsCanvas,
            text = " ",
            bg = self.farbeDockCanvasesBackground,
            fg = self.farbeDockCanvasesForeground,
            font = ("Piboto", int(fontSizeFaktor*40))
        )

        self.anzeigeKalibrierungsErgebnisse.place(x = self.meinCanvas.winfo_width()/2, y = self.meinCanvas.winfo_height()/2, anchor = "s")


        self.root.update()

        versuchNr = 1
        messungNr = 0
        anzahlKorrekterMessergebnisse = 0
        bleibInWhileSchleife = True

        vorherigerDrehmomentWert = self.zugriffAufApp.MesswertObjekte["Drehmoment"].value
        vorherigerSchubWert = self.zugriffAufApp.MesswertObjekte["Schub"].value

        while (versuchNr <= 10) & (bleibInWhileSchleife):

            istFehlerfrei = self.zugriffAufApp.meinUSBhandler.leseUSBline()
            if istFehlerfrei:
                for key in self.zugriffAufApp.MesswertObjekte:
                    self.zugriffAufApp.MesswertObjekte[key].refreshYourValue(self.zugriffAufApp.meinUSBhandler.data, self.zugriffAufApp.meinConfigHandler.modocKonstanten)
                drehmoment = self.zugriffAufApp.MesswertObjekte["Drehmoment"].value
                schub = self.zugriffAufApp.MesswertObjekte["Schub"].value

            messungNr = messungNr + 1

            if messungNr == 5:
                messungNr = 0

                if (schub == vorherigerSchubWert) & (drehmoment == vorherigerDrehmomentWert):
                    anzahlKorrekterMessergebnisse = anzahlKorrekterMessergebnisse + 1
                else:
                    anzahlKorrekterMessergebnisse = 1
                    versuchNr = versuchNr + 1
                    vorherigerDrehmomentWert = drehmoment
                    vorherigerSchubWert = schub

                if anzahlKorrekterMessergebnisse == 5:
                    bleibInWhileSchleife = False

            self.anzeigeKalibrierungsErgebnisse.config(text = str(versuchNr) + ". Versuch.. (" + str(anzahlKorrekterMessergebnisse) + ". Messwert) Drehmoment: " + str(vorherigerDrehmomentWert) + " / " + str(drehmoment) + "   Schub: " + str(vorherigerSchubWert) + " / " + str(schub))
            self.root.update()


        if bleibInWhileSchleife == False:
            self.zugriffAufApp.meinConfigHandler.modocKonstanten["drehmoment_kal"] = int(self.zugriffAufApp.meinConfigHandler.modocKonstanten["drehmoment_kal"] - drehmoment)
            self.zugriffAufApp.meinConfigHandler.modocKonstanten["schub_kal"] = int(self.zugriffAufApp.meinConfigHandler.modocKonstanten["schub_kal"] - schub)
            self.zugriffAufApp.meinConfigHandler.modocConfigSchreiben()
            self.zugriffAufApp.meinConfigHandler.modocConfigLesen()
            self.anzeigeKalibrierungsErgebnisse.config(text = "OK, neue Kalibrationswerte: " + str(self.zugriffAufApp.meinConfigHandler.modocKonstanten["drehmoment_kal"]) + " bzw. " + str(self.zugriffAufApp.meinConfigHandler.modocKonstanten["schub_kal"]))
        else:
            self.anzeigeKalibrierungsErgebnisse.config(text = "Kalibration fehlgeschlagen!")
        self.root.update()
        time.sleep(3.5)
        self.kalibrierenEnde()



    def anmeldeFensterNachUnten(self):
        if self.userAnmeldungCanvas != None:
            self.userLabelArray[self.ausgewaehlterUserIndexInUserLabelArray].config(bg = self.farbeDockCanvasesBackground, fg=self.farbeDockCanvasesForeground)
            self.ausgewaehlterUserIndexInUserLabelArray = self.ausgewaehlterUserIndexInUserLabelArray + 1
            if(self.ausgewaehlterUserIndexInUserLabelArray == self.userLabelCounter):
                self.ausgewaehlterUserIndexInUserLabelArray = 0
            self.userLabelArray[self.ausgewaehlterUserIndexInUserLabelArray].config(bg = "#2F6ADE", fg="white")
        else:
            print("Keine aktive Anmeldung")

    def anmeldeFensterNachOben(self):
        if self.userAnmeldungCanvas != None:
            self.userLabelArray[self.ausgewaehlterUserIndexInUserLabelArray].config(bg = self.farbeDockCanvasesBackground, fg=self.farbeDockCanvasesForeground)
            self.ausgewaehlterUserIndexInUserLabelArray = self.ausgewaehlterUserIndexInUserLabelArray - 1
            if(self.ausgewaehlterUserIndexInUserLabelArray == -1):
                self.ausgewaehlterUserIndexInUserLabelArray = self.userLabelCounter - 1
            self.userLabelArray[self.ausgewaehlterUserIndexInUserLabelArray].config(bg = "#2F6ADE", fg="white")
        else:
            print("Keine aktive Anmeldung")

    def userAnmeldung(self):

        self.aktiveAnmeldung = True

        filesInDirectory = [file for file in os.listdir(".") if os.path.isfile(os.path.join(".", file))]
        filesInDirectory.sort()

        self.userAnmeldungCanvas = Canvas(self.root, width=self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterBreite"], height=self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterHoehe"], bg=self.farbeDockCanvasesBackground)
        self.userAnmeldungCanvas.place(x = 0, y = 0, anchor="nw")

        self.root.update()

        self.userLabelArray = np.array([])
        self.ausgewaehlterUserIndexInUserLabelArray = 0
        self.userLabelCounter = 0
        for file in filesInDirectory:
            if file.startswith("config_") and file != "config_login.csv":
                self.userLabelArray = np.append(self.userLabelArray, [Label(
                    self.userAnmeldungCanvas,
                    bg = self.farbeDockCanvasesBackground,
                    fg = self.farbeDockCanvasesForeground,
                    text = file,
                    font = ("Piboto", int(fontSizeFaktor*18))
                )])
                self.userLabelArray[self.userLabelCounter].place(
                    x = self.abstandZumRand*2,
                    y=self.abstandZumRand*4 + int(fontSizeFaktor*18+15)*self.userLabelCounter
                )
                self.userLabelCounter = self.userLabelCounter + 1
        self.userLabelArray[self.ausgewaehlterUserIndexInUserLabelArray].config(bg = "#2F6ADE", fg="white")

        self.userTastenLabels = {
            "1": Label(
                self.userAnmeldungCanvas,
                text = " 1 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "2": Label(
                self.userAnmeldungCanvas,
                text = " 2 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "3": Label(
                self.userAnmeldungCanvas,
                text = " 3 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "4": Label(
                self.userAnmeldungCanvas,
                text = " 4 ",
                bg = "#2F6ADE",
                fg = "white",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize)))
            ),
            "Rauf": Label(
                self.userAnmeldungCanvas,
                text = "Up",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Runter": Label(
                self.userAnmeldungCanvas,
                text = "Down",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Auswaehlen": Label(
                self.userAnmeldungCanvas,
                text = " Enter",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            ),
            "Abbrechen": Label(
                self.userAnmeldungCanvas,
                text = " Abbrechen",
                bg = self.farbeDockCanvasesBackground,
                fg = "#2F6ADE",
                font = (self.dockFont, int(fontSizeFaktor*int(self.dockFontSize*0.6)), 'bold')
            )
        }

        self.userTastenLabels["1"].place(
            x = self.meinCanvas.winfo_width()/2 - 150,
            y = self.meinCanvas.winfo_height()*0.9,
            anchor="c"
        )
        self.userTastenLabels["2"].place(
            x = self.meinCanvas.winfo_width()/2 - 50,
            y = self.meinCanvas.winfo_height()*0.9,
            anchor="c"
        )
        self.userTastenLabels["3"].place(
            x = self.meinCanvas.winfo_width()/2 + 50,
            y = self.meinCanvas.winfo_height()*0.9,
            anchor="c"
        )
        self.userTastenLabels["4"].place(
            x = self.meinCanvas.winfo_width()/2 + 150,
            y = self.meinCanvas.winfo_height()*0.9,
            anchor="c"
        )
        self.userTastenLabels["Rauf"].place(
            x = self.meinCanvas.winfo_width()/2 - 150,
            y = self.meinCanvas.winfo_height()*0.9+35,
            anchor="c"
        )
        self.userTastenLabels["Runter"].place(
            x = self.meinCanvas.winfo_width()/2 - 50,
            y = self.meinCanvas.winfo_height()*0.9+35,
            anchor="c"
        )
        self.userTastenLabels["Auswaehlen"].place(
            x = self.meinCanvas.winfo_width()/2 + 50,
            y = self.meinCanvas.winfo_height()*0.9+35,
            anchor="c"
        )
        self.userTastenLabels["Abbrechen"].place(
            x = self.meinCanvas.winfo_width()/2 + 150,
            y = self.meinCanvas.winfo_height()*0.9+35,
            anchor="c"
        )

        self.root.update()

    def userAnmeldungFortsetzung(self):
        # try: # Versuch das Value zu entpacken
        #eingabeUserName = self.benutzerAufforderungEntry.get()

        if self.aktiveAnmeldung:

            userName = self.userLabelArray[self.ausgewaehlterUserIndexInUserLabelArray]["text"][7:len(self.userLabelArray[self.ausgewaehlterUserIndexInUserLabelArray]["text"])-4]

            self.benutzerStringVar.set("Benutzer: " + userName)

            try: # Versuch die Datei zu öffnen
                configfilename = "config_" + userName + ".csv"
                configfileVersuch = csv.reader(open(configfilename, "r"), delimiter=";")

                self.restartCommand(userName)

            except FileNotFoundError:
                if self.wUserFehlerfeld == None:
                    self.wUserFehlerfeld = Label(self.userAnmeldungCanvas, text="Kein Config-File für diesen Benutzer!",font = ("Piboto", int(fontSizeFaktor*12)), fg="red")
                    self.wUserFehlerfeld.place(x=self.abstandZumRand*2, y=self.abstandZumRand*4, anchor="nw")

            self.aktiveAnmeldung = False
            try:
                self.userAnmeldungCanvas.destroy()
            except:
                print("Canvas konnte nicht zerstört werden")
            self.userAnmeldungCanvas = None
            self.userLabelCounter = 0
            self.userTastenLabels = None

        else:
            print("Keine aktive Anmeldung")

    def userAnmeldungAbbrechen(self):

        if self.aktiveAnmeldung:
            self.userAnmeldungCanvas.destroy()
        else:
            print("Keine aktive Anmeldung")
        self.aktiveAnmeldung = False
        self.userAnmeldungCanvas = None
        self.userLabelCounter = 0
        self.userTastenLabels = None

    def testbeschreibungBereinigen(self):

        self.Testbeschreibung = self.testbeschreibungEingabe.get()
        self.Testbeschreibung = self.Testbeschreibung.strip()                   # Spaces am Beginn und Ende entfernen
        a = ""
        for c in self.Testbeschreibung:
                if (c.isalnum()                                 # Alphanumerische Zeichen ok 
                or c == " "                                         # und auch diese..
                or c == "-"
                or c == "_"
                or c == "+"
                or c == "&"
                ):
                        a += c
        self.Testbeschreibung = a [:40]             # Abschneiden auf die ersten 40 Zeichen
                 
    def testbeschreibungEingebenCheckButton(self):      # Text bereinigen und nochmal anzeigen

        self.testbeschreibungBereinigen()             

        self.testbeschreibungEingebenCanvas.destroy()
        self.zugriffAufApp.guiReset()
        self.testbeschreibungEingeben()
    
    def testbeschreibungEingebenEnter(self, event):     # Text bereinigen und Menü beenden
        self.testbeschreibungEingebenOKButton()
        
    def testbeschreibungEingebenOKButton(self):     # Text bereinigen und Menü beenden

        self.testbeschreibungBereinigen()             

        self.testbeschreibungEingebenCanvas.destroy()
        self.zugriffAufApp.guiReset()

    def testbeschreibungEingeben(self):
        print("Testbeschreibung eingeben!")

        self.aktiveTestbeschreibungEingeben = True

        self.testbeschreibungEingebenCanvas = Canvas(
            self.root,
            width = self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterBreite"],
            height = self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterHoehe"],
            bg = self.farbeDockCanvasesBackground
        )
        self.testbeschreibungEingebenCanvas.place(x = 0, y = 0, anchor = "nw")

        self.testbeschreibungAuffordern = self.testbeschreibungEingebenCanvas.create_text(
            (
                self.meinCanvas.winfo_width()/2,
                self.meinCanvas.winfo_height()/2 - 50
            ),
            text = "40 Zeichen max eingeben (auch -_+&), Check zur Prüfung, OK oder Enter-Taste zum Speichern. Wenn ScreenShot gedrueckt wird entsteht nnnn_Text.png",
            anchor = "s",
            fill = self.farbeDockCanvasesForeground,
            font = ("Piboto", int(fontSizeFaktor*18))
        )

        self.testbeschreibungEingabe = Entry(self.testbeschreibungEingebenCanvas, font = ("courier", int(fontSizeFaktor*24)))
        self.testbeschreibungEingabe.insert(END, self.Testbeschreibung) 
        self.testbeschreibungEingabe.place(
                x=self.meinCanvas.winfo_width()/2,
                y=self.meinCanvas.winfo_height()/2 - 10,
                width=fontSizeFaktor*800,
                anchor="s")
        self.testbeschreibungEingabe.focus()
                
        self.testbeschreibungEingabeCheck = Button(self.testbeschreibungEingebenCanvas, text="Check", command=self.testbeschreibungEingebenCheckButton)
        self.testbeschreibungEingabeCheck.place(
                x=self.meinCanvas.winfo_width()/1.6 - 100,
                y=self.meinCanvas.winfo_height()/2 + 30,
                anchor="s")

        self.testbeschreibungEingabeOK = Button(self.testbeschreibungEingebenCanvas, text="OK", command=self.testbeschreibungEingebenOKButton)
        self.testbeschreibungEingabeOK.place(
                x=self.meinCanvas.winfo_width()/1.6,
                y=self.meinCanvas.winfo_height()/2 + 30,
                anchor="s")
                
        self.root.bind('<Return>', self.testbeschreibungEingebenEnter)

    def screenshotAusloesen(self):

        self.screenShootAlarmanzeige = Alarmanzeige(
            self.root,
            self.meinCanvas,
            "  Screenshoot ...  ",
            True
        )
        self.screenShootAlarmanzeige.zeichnen()
        self.root.update()
        time.sleep(0.2)
        self.screenShootAlarmanzeige.delete()
        self.root.update()

        self.statusfilename = "screenshootready.txt"
        if rasp  == 1:
            self.statusfilename = "/home/sp/configFiles/" + self.statusfilename

        if os.path.exists (self.statusfilename):
            os.remove (self.statusfilename)
            print ("ScreenShot Statusfile: ", self.statusfilename, " war vorhanden - wurde gelöscht!")                  # Weil nun vom letzten Screenshoot das Statusfile gelöscht wurde,
                                                                                                                                                                                      # kann NACH dem Bash-Aufruf geprüft werden, ob es nun NEU angelegt wurde
        else:
            print ("ScreenShot Statusfile: ", self.statusfilename, " nicht gefunden!")

        scriptcall="/home/sp/bashScripts/screenShot " + "'" + self.Testbeschreibung + "'"
            # Achtung: damit in self.Testbeschreibung auch Blanks drinn sein können muss das mit EINFACHEN Hochkommas eingefasst sein. 
            # ... das sind also: Doppelte-Einfache-Doppelte
        os.system(scriptcall)

        try:
            self.statusfile = open(self.statusfilename, "r")
        except FileNotFoundError:
            print ("ScreenShot Statusfile: ", self.statusfilename, " nicht gefunden!")
            resulttext = "  Screenshoot fehlgeschlagen - Memorystick vorhanden?  "
            resulttime = 5
        else:
            for line in self.statusfile:
                screenshotNumber = line.rstrip()
            self.statusfile.close()
            resulttext = "  Screenshoot " + screenshotNumber + " erstellt  "
            resulttime = 1

        self.screenShootAlarmanzeige = Alarmanzeige(
            self.root,
            self.meinCanvas,
            resulttext,
#            self.Design
            True
        )
        self.screenShootAlarmanzeige.zeichnen()
        self.root.update()
        time.sleep(resulttime)
        self.screenShootAlarmanzeige.delete()


class RundinstrumentenGruppe:

    def __init__ (self, eingabeRoot, eingabeCanvas, eingabeMessobjekte, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeSchattenXoffset, eingabeSchattenYoffset, eingabeAbstandZwischenRundinstrumenten):

        self.root = eingabeRoot
        self.meinCanvas = eingabeCanvas
        self.meineMessobjekte = None

        self.abstand = eingabeAbstandZwischenRundinstrumenten
        self.halberAbstand = eingabeAbstandZwischenRundinstrumenten/2

        if len(eingabeMessobjekte) > 8:
            self.meineMessobjekte = eingabeMessobjekte[0:8]
            print("Zu viele Rundinstrumente in dieser Gruppe!")
        else:
            self.meineMessobjekte = eingabeMessobjekte

        self.einzelneRundinstrumentPositionen = np.array([])
        self.allgemeinerRadius = None

        self.update(eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2)

        self.meineRundinstrumente = np.array([])

        for einMessobjekt, einePosition  in zip(self.meineMessobjekte, self.einzelneRundinstrumentPositionen):
            self.meineRundinstrumente = np.append(self.meineRundinstrumente, [Rundinstrument(
                self.root,
                self.meinCanvas,
                einMessobjekt,
                einePosition[0],
                einePosition[1],
                einePosition[2],
                einePosition[3],
                self.allgemeinerRadius,
                eingabeSchattenXoffset,
                eingabeSchattenYoffset)
            ])

    def update(self, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2):
        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2

        # Array mit einzelnen Positionen der Rundinstrumente
        self.einzelneRundinstrumentPositionen = np.array([])

        breiteHalbe = (self.posX2 - self.posX1)/2
        hoeheHalbe = (self.posY2 - self.posY1)/2

        if len(self.meineMessobjekte) < 5:
            if len(self.meineMessobjekte) == 1:
                if (self.posX2-self.posX1) >= (self.posY2-self.posY1):
                    self.allgemeinerRadius = (self.posY2-self.posY1)/2
                    self.einzelneRundinstrumentPositionen = np.array([np.array([
                        self.posX1 + breiteHalbe - self.allgemeinerRadius,
                        self.posX1 + breiteHalbe + self.allgemeinerRadius,
                        self.posY1,
                        self.posY2
                    ])])
                else:
                    self.allgemeinerRadius = (self.posX2-self.posX1)/2
                    self.einzelneRundinstrumentPositionen = np.array([np.array([
                        self.posX1,
                        self.posX2,
                        self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                        self.posY1 + hoeheHalbe + self.allgemeinerRadius
                    ])])

            elif len(self.meineMessobjekte) == 2:
                # Zwei Rundinstrumente
                if min(self.posY2-self.posY1, (self.posX2-self.posX1)/2-self.abstand) >= min(self.posX2-self.posX1, (self.posY2-self.posY1)/2-self.abstand):
                    # Die Rundinstrumente sollen nebeneinander sein -> Radius = Höhe
                    self.allgemeinerRadius = min(self.posY2-self.posY1, (self.posX2-self.posX1)/2-self.abstand)/2

                    oberePosY = self.posY1 + (self.posY2 - self.posY1)/2 - self.allgemeinerRadius
                    unterePosY = self.posY1 + (self.posY2 - self.posY1)/2 + self.allgemeinerRadius

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            oberePosY,
                            unterePosY
                        ]),
                    ])
                else:
                    # Die Rundinstrumente sollen übereinander sein -> Radius = Breite
                    self.allgemeinerRadius = min(self.posX2-self.posX1, (self.posY2-self.posY1)/2-self.abstand)/2

                    linkePosX = self.posX1 + (self.posX2 - self.posX1)/2 - self.allgemeinerRadius
                    RechtePosX = self.posX1 + (self.posX2 - self.posX1)/2 + self.allgemeinerRadius

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ])
                    ])

            elif len(self.meineMessobjekte) == 3:
                # Drei Rundinstrumente

                kandidat1 = min((self.posX2-self.posX1), (self.posY2-self.posY1)/3-2*self.abstand)/2
                kandidat2 = min((self.posX2-self.posX1)/3-2*self.abstand, (self.posY2-self.posY1))/2
                kandidat3 = min((self.posX2-self.posX1)/2-self.abstand, (self.posY2-self.posY1)/2-self.abstand)/2

                if (kandidat2 >= kandidat1) & (kandidat2 >= kandidat3):
                    # Die Rundinstrumente sollen nebeneinander sein -> Radius = Höhe
                    self.allgemeinerRadius = kandidat2

                    oberePosY = self.posY1 + (self.posY2 - self.posY1)/2 - self.allgemeinerRadius
                    unterePosY = self.posY1 + (self.posY2 - self.posY1)/2 + self.allgemeinerRadius

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posX1 + breiteHalbe - self.allgemeinerRadius -self.abstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - self.allgemeinerRadius,
                            self.posX1 + breiteHalbe + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.allgemeinerRadius + self.abstand,
                            self.posX1 + breiteHalbe + 3*self.allgemeinerRadius + self.abstand,
                            oberePosY,
                            unterePosY
                        ])
                    ])
                elif (kandidat1 > kandidat2) & (kandidat1 > kandidat3):
                    # Die Rundinstrumente sollen übereinander sein -> Radius = Breite
                    self.allgemeinerRadius = kandidat1

                    linkePosX = self.posX1 + (self.posX2 - self.posX1)/2 - self.allgemeinerRadius
                    RechtePosX = self.posX1 + (self.posX2 - self.posX1)/2 + self.allgemeinerRadius

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius - self.abstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius + self.abstand,
                            self.posY1 + hoeheHalbe + 3*self.allgemeinerRadius + self.abstand
                        ])
                    ])
                else:
                    self.allgemeinerRadius = kandidat3

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - self.allgemeinerRadius,
                            self.posX1 + breiteHalbe + self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ])
                    ])


            elif len(self.meineMessobjekte) == 4:
                # Vier Rundinstrumente

                kandidat1 = min((self.posX2-self.posX1), (self.posY2-self.posY1)/4-3*self.abstand)/2
                kandidat2 = min((self.posX2-self.posX1)/4-3*self.abstand, (self.posY2-self.posY1))/2
                kandidat3 = min((self.posX2-self.posX1)/2-self.abstand, (self.posY2-self.posY1)/2-self.abstand)/2

                if (kandidat2 >= kandidat1) & (kandidat2 >= kandidat3):
                    # nebeneinander
                    self.allgemeinerRadius = kandidat2

                    oberePosY = self.posY1 + (self.posY2 - self.posY1)/2 - self.allgemeinerRadius
                    unterePosY = self.posY1 + (self.posY2 - self.posY1)/2 + self.allgemeinerRadius

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 4*self.allgemeinerRadius - 3*self.halberAbstand,
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - 3*self.halberAbstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + 3*self.halberAbstand,
                            self.posX1 + breiteHalbe + 4*self.allgemeinerRadius + 3*self.halberAbstand,
                            oberePosY,
                            unterePosY
                        ])
                    ])



                elif (kandidat1 > kandidat2) & (kandidat1 > kandidat3):
                    # übereinander
                    self.allgemeinerRadius = kandidat1

                    linkePosX = self.posX1 + (self.posX2 - self.posX1)/2 - self.allgemeinerRadius
                    RechtePosX = self.posX1 + (self.posX2 - self.posX1)/2 + self.allgemeinerRadius

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - 4*self.allgemeinerRadius - 3*self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - 3*self.halberAbstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + 3*self.halberAbstand,
                            self.posY1 + hoeheHalbe + 4*self.allgemeinerRadius + 3*self.halberAbstand
                        ]),
                    ])

                else:
                    # quadrat
                    self.allgemeinerRadius = kandidat3

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ])
                    ])

        else:
            if len(self.meineMessobjekte) == 5:
                # Fünf Rundinstrumente
                kandidat1 = min((self.posX2-self.posX1), (self.posY2-self.posY1)/5-4*self.abstand)/2
                kandidat2 = min((self.posX2-self.posX1)/5-4*self.abstand, (self.posY2-self.posY1))/2
                kandidat3 = min((self.posX2-self.posX1)/3-2*self.abstand, (self.posY2-self.posY1)/2-self.abstand)/2
                kandidat4 = min((self.posX2-self.posX1)/2-self.abstand, (self.posY2-self.posY1)/3-2*self.abstand)/2

                if (kandidat2 >= kandidat1) & (kandidat2 >= kandidat3) & (kandidat2 >= kandidat4):
                    # nebeneinander
                    self.allgemeinerRadius = kandidat2

                    oberePosY = self.posY1 + (self.posY2 - self.posY1)/2 - self.allgemeinerRadius
                    unterePosY = self.posY1 + (self.posY2 - self.posY1)/2 + self.allgemeinerRadius

                    breiteHalbe = (self.posX2 - self.posX1)/2

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 5*self.allgemeinerRadius - 2*self.abstand,
                            self.posX1 + breiteHalbe - 3*self.allgemeinerRadius - 2*self.abstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posX1 + breiteHalbe - self.allgemeinerRadius - self.abstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - self.allgemeinerRadius,
                            self.posX1 + breiteHalbe + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.allgemeinerRadius + self.abstand,
                            self.posX1 + breiteHalbe + 3*self.allgemeinerRadius + self.abstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + 3*self.allgemeinerRadius + 2*self.abstand,
                            self.posX1 + breiteHalbe + 5*self.allgemeinerRadius + 2*self.abstand,
                            oberePosY,
                            unterePosY
                        ])
                    ])



                elif (kandidat1 > kandidat2) & (kandidat1 > kandidat3) & (kandidat1 > kandidat4):
                    # übereinander
                    self.allgemeinerRadius = kandidat1

                    linkePosX = self.posX1 + (self.posX2 - self.posX1)/2 - self.allgemeinerRadius
                    RechtePosX = self.posX1 + (self.posX2 - self.posX1)/2 + self.allgemeinerRadius
                    hoeheHalbe = (self.posY2 - self.posY1)/2

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - 5*self.allgemeinerRadius - 2*self.abstand,
                            self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - 2*self.abstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius - self.abstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius + self.abstand,
                            self.posY1 + hoeheHalbe + 3*self.allgemeinerRadius + self.abstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe + 3*self.allgemeinerRadius + 2*self.abstand,
                            self.posY1 + hoeheHalbe + 5*self.allgemeinerRadius + 2*self.abstand
                        ])
                    ])

                elif (kandidat3 > kandidat2) & (kandidat3 > kandidat1) & (kandidat3 > kandidat4):
                    # 2 Zeilen
                    self.allgemeinerRadius = kandidat3

                    breiteHalbe = (self.posX2 - self.posX1)/2
                    hoeheHalbe = (self.posY2 - self.posY1)/2

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posX1 + breiteHalbe - self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - self.allgemeinerRadius,
                            self.posX1 + breiteHalbe + self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.allgemeinerRadius + self.abstand,
                            self.posX1 + breiteHalbe + 3*self.allgemeinerRadius + self.abstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ])
                    ])
                else:
                    # 3 Zeilen
                    self.allgemeinerRadius = kandidat4

                    breiteHalbe = (self.posX2 - self.posX1)/2
                    hoeheHalbe = (self.posY2 - self.posY1)/2

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius - self.abstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius - self.abstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - self.allgemeinerRadius,
                            self.posX1 + breiteHalbe + self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius + self.abstand,
                            self.posY1 + hoeheHalbe + 3*self.allgemeinerRadius + self.abstand
                        ])
                    ])


            elif len(self.meineMessobjekte) == 6:
                # Sechs Rundinstrumente
                kandidat1 = min((self.posX2-self.posX1), (self.posY2-self.posY1)/6-5*self.abstand)/2
                kandidat2 = min((self.posX2-self.posX1)/6-1*self.abstand, (self.posY2-self.posY1))/2
                kandidat3 = min((self.posX2-self.posX1)/3-2*self.abstand, (self.posY2-self.posY1)/2-self.abstand)/2
                kandidat4 = min((self.posX2-self.posX1)/2-self.abstand, (self.posY2-self.posY1)/3-3*self.abstand)/2

                if (kandidat2 >= kandidat1) & (kandidat2 >= kandidat3) & (kandidat2 >= kandidat4):
                    # nebeneinander
                    self.allgemeinerRadius = kandidat2

                    oberePosY = self.posY1 + (self.posY2 - self.posY1)/2 - self.allgemeinerRadius
                    unterePosY = self.posY1 + (self.posY2 - self.posY1)/2 + self.allgemeinerRadius

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 6*self.allgemeinerRadius - 5*self.halberAbstand,
                            self.posX1 + breiteHalbe - 4*self.allgemeinerRadius - 5*self.halberAbstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 4*self.allgemeinerRadius - 3*self.halberAbstand,
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - 3*self.halberAbstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + 3*self.halberAbstand,
                            self.posX1 + breiteHalbe + 4*self.allgemeinerRadius + 3*self.halberAbstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + 4*self.allgemeinerRadius + 5*self.halberAbstand,
                            self.posX1 + breiteHalbe + 6*self.allgemeinerRadius + 5*self.halberAbstand,
                            oberePosY,
                            unterePosY
                        ])
                    ])

                elif (kandidat1 > kandidat2) & (kandidat1 > kandidat3) & (kandidat1 > kandidat4):
                    # übereinander
                    self.allgemeinerRadius = kandidat1

                    linkePosX = self.posX1 + (self.posX2 - self.posX1)/2 - self.allgemeinerRadius
                    RechtePosX = self.posX1 + (self.posX2 - self.posX1)/2 + self.allgemeinerRadius

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - 6*self.allgemeinerRadius - 5*self.halberAbstand,
                            self.posY1 + hoeheHalbe - 4*self.allgemeinerRadius - 5*self.halberAbstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - 4*self.allgemeinerRadius - 3*self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - 3*self.halberAbstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + 3*self.halberAbstand,
                            self.posY1 + hoeheHalbe + 4*self.allgemeinerRadius + 3*self.halberAbstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe + 4*self.allgemeinerRadius + 5*self.halberAbstand,
                            self.posY1 + hoeheHalbe + 6*self.allgemeinerRadius + 5*self.halberAbstand
                        ])
                    ])

                elif (kandidat3 > kandidat2) & (kandidat3 > kandidat1) & (kandidat3 > kandidat4):
                    # 2 Zeilen
                    self.allgemeinerRadius = kandidat3

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posX1 + breiteHalbe - self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - self.allgemeinerRadius,
                            self.posX1 + breiteHalbe + self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.allgemeinerRadius + self.abstand,
                            self.posX1 + breiteHalbe + 3*self.allgemeinerRadius + self.abstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posX1 + breiteHalbe - self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - self.allgemeinerRadius,
                            self.posX1 + breiteHalbe + self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.allgemeinerRadius + self.abstand,
                            self.posX1 + breiteHalbe + 3*self.allgemeinerRadius + self.abstand,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ])
                    ])
                else:
                    # 3 Zeilen

                    self.allgemeinerRadius = kandidat4

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius - self.abstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius - self.abstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius + self.abstand,
                            self.posY1 + hoeheHalbe + 3*self.allgemeinerRadius + self.abstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius + self.abstand,
                            self.posY1 + hoeheHalbe + 3*self.allgemeinerRadius + self.abstand
                        ])
                    ])


            elif len(self.meineMessobjekte) == 7:

                kandidat1 = min((self.posX2-self.posX1), (self.posY2-self.posY1)/7-6*self.abstand)/2       # Kandidat fuer Anordnung 1 Zeile
                kandidat2 = min((self.posX2-self.posX1)/7-1*self.abstand, (self.posY2-self.posY1))/2       # Kandidat fuer Anordnung 7 Zeilen
                kandidat3 = min((self.posX2-self.posX1)/4-3*self.abstand, (self.posY2-self.posY1)/2-self.abstand)/2     # Kandidat fuer Anordnung 2 Zeilen
                kandidat4 = min((self.posX2-self.posX1)/2-self.abstand, (self.posY2-self.posY1)/4-3*self.abstand)/2     # Kandidat fuer Anordnung 4 Zeilen
                kandidat5 = min((self.posX2-self.posX1)/3-2*self.abstand, (self.posY2-self.posY1)/3-2*self.abstand)/2     # Kandidat fuer Anordnung 3 Zeilen

                if (kandidat2 >= kandidat1) & (kandidat2 >= kandidat3) & (kandidat2 >= kandidat4) & (kandidat2 >= kandidat5):
                    # nebeneinander
                    self.allgemeinerRadius = kandidat2

                    oberePosY = self.posY1 + (self.posY2 - self.posY1)/2 - self.allgemeinerRadius
                    unterePosY = self.posY1 + (self.posY2 - self.posY1)/2 + self.allgemeinerRadius

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 7*self.allgemeinerRadius - 3*self.abstand,
                            self.posX1 + breiteHalbe - 5*self.allgemeinerRadius - 3*self.abstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 5*self.allgemeinerRadius - 2*self.abstand,
                            self.posX1 + breiteHalbe - 3*self.allgemeinerRadius - 2*self.abstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posX1 + breiteHalbe - self.allgemeinerRadius -self.abstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - self.allgemeinerRadius,
                            self.posX1 + breiteHalbe + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.allgemeinerRadius + self.abstand,
                            self.posX1 + breiteHalbe + 3*self.allgemeinerRadius + self.abstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + 3*self.allgemeinerRadius + 2*self.abstand,
                            self.posX1 + breiteHalbe + 5*self.allgemeinerRadius + 2*self.abstand,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + 5*self.allgemeinerRadius + 3*self.abstand,
                            self.posX1 + breiteHalbe + 7*self.allgemeinerRadius + 3*self.abstand,
                            oberePosY,
                            unterePosY
                        ])
                    ])



                elif (kandidat1 > kandidat2) & (kandidat1 > kandidat3) & (kandidat1 > kandidat4) & (kandidat1 > kandidat5):
                    # übereinander
                    self.allgemeinerRadius = kandidat1

                    linkePosX = self.posX1 + (self.posX2 - self.posX1)/2 - self.allgemeinerRadius
                    RechtePosX = self.posX1 + (self.posX2 - self.posX1)/2 + self.allgemeinerRadius

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - 7*self.allgemeinerRadius - 3*self.abstand,
                            self.posY1 + hoeheHalbe - 5*self.allgemeinerRadius - 3*self.abstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - 5*self.allgemeinerRadius - 2*self.abstand,
                            self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - 2*self.abstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius - self.abstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius + self.abstand,
                            self.posY1 + hoeheHalbe + 3*self.allgemeinerRadius + self.abstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe + 3*self.allgemeinerRadius + 2*self.abstand,
                            self.posY1 + hoeheHalbe + 5*self.allgemeinerRadius + 2*self.abstand
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + hoeheHalbe + 5*self.allgemeinerRadius + 3*self.abstand,
                            self.posY1 + hoeheHalbe + 7*self.allgemeinerRadius + 3*self.abstand
                        ])
                    ])

                elif (kandidat3 > kandidat2) & (kandidat3 > kandidat1) & (kandidat3 > kandidat4):
                    # 2 Zeilen
                    self.allgemeinerRadius = kandidat3

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 4*self.allgemeinerRadius - 3*self.halberAbstand,
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - 3*self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius -self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe -self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius -self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + 3*self.halberAbstand,
                            self.posX1 + breiteHalbe + 4*self.allgemeinerRadius + 3*self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius -self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posX1 + breiteHalbe - self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - self.allgemeinerRadius,
                            self.posX1 + breiteHalbe + self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.allgemeinerRadius + self.abstand,
                            self.posX1 + breiteHalbe + 3*self.allgemeinerRadius + self.abstand,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ])
                    ])

                elif (kandidat4 > kandidat1) & (kandidat4 > kandidat2) & (kandidat4 > kandidat3) & (kandidat4 > kandidat5):
                    # 4 Zeilen
                    self.allgemeinerRadius = kandidat4

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            self.posY1 + hoeheHalbe - 4*self.allgemeinerRadius - 3*self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - 3*self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            self.posY1 + hoeheHalbe - 4*self.allgemeinerRadius - 3*self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - 3*self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posY1 + hoeheHalbe - self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                            self.posX1 + breiteHalbe - self.halberAbstand,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.halberAbstand,
                            self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                            self.posY1 + hoeheHalbe + self.halberAbstand,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - self.allgemeinerRadius,
                            self.posX1 + breiteHalbe + self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + 3*self.halberAbstand,
                            self.posY1 + hoeheHalbe + 4*self.allgemeinerRadius + 3*self.halberAbstand
                        ])
                    ])
                else:
                    #3 Zeilen
                    self.allgemeinerRadius = kandidat5

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + breiteHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posX1 + breiteHalbe - self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius - self.abstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - self.allgemeinerRadius,
                            self.posX1 + breiteHalbe + self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius - self.abstand
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.allgemeinerRadius + self.abstand,
                            self.posX1 + breiteHalbe + 3*self.allgemeinerRadius + self.abstand,
                            self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius - self.abstand
                        ]),

                        np.array([
                            self.posX1 + breiteHalbe - 3*self.allgemeinerRadius - self.abstand,
                            self.posX1 + breiteHalbe - self.allgemeinerRadius - self.abstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - self.allgemeinerRadius,
                            self.posX1 + breiteHalbe + self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe + self.allgemeinerRadius + self.abstand,
                            self.posX1 + breiteHalbe + 3*self.allgemeinerRadius + self.abstand,
                            self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius
                        ]),
                        np.array([
                            self.posX1 + breiteHalbe - self.allgemeinerRadius,
                            self.posX1 + breiteHalbe + self.allgemeinerRadius,
                            self.posY1 + hoeheHalbe + self.allgemeinerRadius + self.abstand,
                            self.posY1 + hoeheHalbe + 3*self.allgemeinerRadius + self.abstand
                        ])
                    ])

            elif len(self.meineMessobjekte) == 8:
                 kandidat1 = min((self.posX2-self.posX1), (self.posY2-self.posY1)/8-7*self.abstand)/2       # Kandidat fuer Anordnung 8 Zeile
                 kandidat2 = min((self.posX2-self.posX1)/8-1*self.abstand, (self.posY2-self.posY1))/2       # Kandidat fuer Anordnung 1 Zeilen
                 kandidat3 = min((self.posX2-self.posX1)/4-3*self.abstand, (self.posY2-self.posY1)/2-self.abstand)/2     # Kandidat fuer Anordnung 2 Zeilen
                 kandidat4 = min((self.posX2-self.posX1)/2-self.abstand, (self.posY2-self.posY1)/4-3*self.abstand)/2     # Kandidat fuer Anordnung 4 Zeilen
                 kandidat5 = min((self.posX2-self.posX1)/3-2*self.abstand, (self.posY2-self.posY1)/3-2*self.abstand)/2     # Kandidat fuer Anordnung 3 Zeilen

                 if (kandidat2 >= kandidat1) & (kandidat2 >= kandidat3) & (kandidat2 >= kandidat4) & (kandidat2 >= kandidat5):
                     # nebeneinander
                     self.allgemeinerRadius = kandidat2

                     oberePosY = self.posY1 + (self.posY2 - self.posY1)/2 - self.allgemeinerRadius
                     unterePosY = self.posY1 + (self.posY2 - self.posY1)/2 + self.allgemeinerRadius

                     self.einzelneRundinstrumentPositionen = np.array([
                         np.array([
                             self.posX1 + breiteHalbe - 8*self.allgemeinerRadius - 7*self.halberAbstand,
                             self.posX1 + breiteHalbe - 6*self.allgemeinerRadius - 7*self.halberAbstand,
                             oberePosY,
                             unterePosY
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe - 6*self.allgemeinerRadius - 5*self.halberAbstand,
                             self.posX1 + breiteHalbe - 4*self.allgemeinerRadius - 5*self.halberAbstand,
                             oberePosY,
                             unterePosY
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe - 4*self.allgemeinerRadius - 3*self.halberAbstand,
                             self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - 3*self.halberAbstand,
                             oberePosY,
                             unterePosY
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                             self.posX1 + breiteHalbe - self.halberAbstand,
                             oberePosY,
                             unterePosY
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + self.halberAbstand,
                             self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                             oberePosY,
                             unterePosY
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + 3*self.halberAbstand,
                             self.posX1 + breiteHalbe + 4*self.allgemeinerRadius + 3*self.halberAbstand,
                             oberePosY,
                             unterePosY
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + 4*self.allgemeinerRadius + 5*self.halberAbstand,
                             self.posX1 + breiteHalbe + 6*self.allgemeinerRadius + 5*self.halberAbstand,
                             oberePosY,
                             unterePosY
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + 6*self.allgemeinerRadius + 7*self.halberAbstand,
                             self.posX1 + breiteHalbe + 8*self.allgemeinerRadius + 7*self.halberAbstand,
                             oberePosY,
                             unterePosY
                         ])
                     ])



                 elif (kandidat1 > kandidat2) & (kandidat1 > kandidat3) & (kandidat1 > kandidat4) & (kandidat1 > kandidat5):
                     # übereinander
                     self.allgemeinerRadius = kandidat1

                     linkePosX = self.posX1 + (self.posX2 - self.posX1)/2 - self.allgemeinerRadius
                     RechtePosX = self.posX1 + (self.posX2 - self.posX1)/2 + self.allgemeinerRadius

                     self.einzelneRundinstrumentPositionen = np.array([
                         np.array([
                             linkePosX,
                             RechtePosX,
                             self.posY1 + hoeheHalbe - 8*self.allgemeinerRadius - 7*self.halberAbstand,
                             self.posY1 + hoeheHalbe - 6*self.allgemeinerRadius - 7*self.halberAbstand
                         ]),
                         np.array([
                             linkePosX,
                             RechtePosX,
                             self.posY1 + hoeheHalbe - 6*self.allgemeinerRadius - 5*self.halberAbstand,
                             self.posY1 + hoeheHalbe - 4*self.allgemeinerRadius - 5*self.halberAbstand
                         ]),
                         np.array([
                             linkePosX,
                             RechtePosX,
                             self.posY1 + hoeheHalbe - 4*self.allgemeinerRadius - 3*self.halberAbstand,
                             self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - 3*self.halberAbstand
                         ]),
                         np.array([
                             linkePosX,
                             RechtePosX,
                             self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                             self.posY1 + hoeheHalbe -self.halberAbstand
                         ]),
                         np.array([
                             linkePosX,
                             RechtePosX,
                             self.posY1 + hoeheHalbe + self.halberAbstand,
                             self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                         ]),
                         np.array([
                             linkePosX,
                             RechtePosX,
                             self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + 3*self.halberAbstand,
                             self.posY1 + hoeheHalbe + 4*self.allgemeinerRadius + 3*self.halberAbstand
                         ]),
                         np.array([
                             linkePosX,
                             RechtePosX,
                             self.posY1 + hoeheHalbe + 4*self.allgemeinerRadius + 5*self.halberAbstand,
                             self.posY1 + hoeheHalbe + 6*self.allgemeinerRadius + 5*self.halberAbstand
                         ]),
                         np.array([
                             linkePosX,
                             RechtePosX,
                             self.posY1 + hoeheHalbe + 6*self.allgemeinerRadius + 7*self.halberAbstand,
                             self.posY1 + hoeheHalbe + 8*self.allgemeinerRadius + 7*self.halberAbstand
                         ])
                     ])

                 elif (kandidat3 > kandidat2) & (kandidat3 > kandidat1) & (kandidat3 > kandidat4):
                     # 2 Zeilen
                     self.allgemeinerRadius = kandidat3

                     self.einzelneRundinstrumentPositionen = np.array([
                         np.array([
                             self.posX1 + breiteHalbe - 4*self.allgemeinerRadius - 3*self.halberAbstand,
                             self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - 3*self.halberAbstand,
                             self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                             self.posY1 + hoeheHalbe - self.halberAbstand
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                             self.posX1 + breiteHalbe - self.halberAbstand,
                             self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                             self.posY1 + hoeheHalbe - self.halberAbstand
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + self.halberAbstand,
                             self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                             self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                             self.posY1 + hoeheHalbe - self.halberAbstand
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + 3*self.halberAbstand,
                             self.posX1 + breiteHalbe + 4*self.allgemeinerRadius + 3*self.halberAbstand,
                             self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                             self.posY1 + hoeheHalbe - self.halberAbstand
                         ]),

                         np.array([
                             self.posX1 + breiteHalbe - 4*self.allgemeinerRadius - 3*self.halberAbstand,
                             self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - 3*self.halberAbstand,
                             self.posY1 + hoeheHalbe + self.halberAbstand,
                             self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe - 2*self.allgemeinerRadius -self.halberAbstand,
                             self.posX1 + breiteHalbe - self.halberAbstand,
                             self.posY1 + hoeheHalbe + self.halberAbstand,
                             self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + self.halberAbstand,
                             self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                             self.posY1 + hoeheHalbe + self.halberAbstand,
                             self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + 3*self.halberAbstand,
                             self.posX1 + breiteHalbe + 4*self.allgemeinerRadius + 3*self.halberAbstand,
                             self.posY1 + hoeheHalbe + self.halberAbstand,
                             self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + self.halberAbstand
                         ])
                     ])

                 elif (kandidat4 > kandidat1) & (kandidat4 > kandidat2) & (kandidat4 > kandidat3) & (kandidat4 > kandidat5):
                     # 4 Zeilen
                     self.allgemeinerRadius = kandidat4

                     self.einzelneRundinstrumentPositionen = np.array([
                         np.array([
                             self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - 5,
                             self.posX1 + breiteHalbe - 5,
                             self.posY1 + hoeheHalbe - 4*self.allgemeinerRadius - 10,
                             self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - 10
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + 5,
                             self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + 5,
                             self.posY1 + hoeheHalbe - 4*self.allgemeinerRadius - 10,
                             self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - 10
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - 5,
                             self.posX1 + breiteHalbe - 5,
                             self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - 5,
                             self.posY1 + hoeheHalbe - 5
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + 5,
                             self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + 5,
                             self.posY1 + hoeheHalbe - 2*self.allgemeinerRadius - 5,
                             self.posY1 + hoeheHalbe - 5
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - 5,
                             self.posX1 + breiteHalbe - 5,
                             self.posY1 + hoeheHalbe + 5,
                             self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + 5
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + 5,
                             self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + 5,
                             self.posY1 + hoeheHalbe + 5,
                             self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + 5
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - 5,
                             self.posX1 + breiteHalbe - 5,
                             self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + 10,
                             self.posY1 + hoeheHalbe + 4*self.allgemeinerRadius + 10
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + 5,
                             self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + 5,
                             self.posY1 + hoeheHalbe + 2*self.allgemeinerRadius + 10,
                             self.posY1 + hoeheHalbe + 4*self.allgemeinerRadius + 10
                         ])
                     ])
                 else:
                     #3 Zeilen
                     self.allgemeinerRadius = kandidat5

                     self.einzelneRundinstrumentPositionen = np.array([
                         np.array([
                             self.posX1 + breiteHalbe - 3*self.allgemeinerRadius - self.abstand,
                             self.posX1 + breiteHalbe - self.allgemeinerRadius - self.abstand,
                             self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - self.abstand,
                             self.posY1 + hoeheHalbe - self.allgemeinerRadius - self.abstand
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe - self.allgemeinerRadius,
                             self.posX1 + breiteHalbe + self.allgemeinerRadius,
                             self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - self.abstand,
                             self.posY1 + hoeheHalbe - self.allgemeinerRadius - self.abstand
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + self.allgemeinerRadius + self.abstand,
                             self.posX1 + breiteHalbe + 3*self.allgemeinerRadius + self.abstand,
                             self.posY1 + hoeheHalbe - 3*self.allgemeinerRadius - self.abstand,
                             self.posY1 + hoeheHalbe - self.allgemeinerRadius - self.abstand
                         ]),

                         np.array([
                             self.posX1 + breiteHalbe - 3*self.allgemeinerRadius - self.abstand,
                             self.posX1 + breiteHalbe - self.allgemeinerRadius -self.abstand,
                             self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                             self.posY1 + hoeheHalbe + self.allgemeinerRadius
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe - self.allgemeinerRadius,
                             self.posX1 + breiteHalbe + self.allgemeinerRadius,
                             self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                             self.posY1 + hoeheHalbe + self.allgemeinerRadius
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + self.allgemeinerRadius + self.abstand,
                             self.posX1 + breiteHalbe + 3*self.allgemeinerRadius + self.abstand,
                             self.posY1 + hoeheHalbe - self.allgemeinerRadius,
                             self.posY1 + hoeheHalbe + self.allgemeinerRadius
                         ]),

                         np.array([
                             self.posX1 + breiteHalbe - 2*self.allgemeinerRadius - self.halberAbstand,
                             self.posX1 + breiteHalbe - self.halberAbstand,
                             self.posY1 + hoeheHalbe + self.allgemeinerRadius + self.abstand,
                             self.posY1 + hoeheHalbe + 3*self.allgemeinerRadius + self.abstand
                         ]),
                         np.array([
                             self.posX1 + breiteHalbe + self.halberAbstand,
                             self.posX1 + breiteHalbe + 2*self.allgemeinerRadius + self.halberAbstand,
                             self.posY1 + hoeheHalbe + self.allgemeinerRadius + self.abstand,
                             self.posY1 + hoeheHalbe + 3*self.allgemeinerRadius + self.abstand
                         ])
                     ])
            else:
                print("Error bei Anordnen der Rundinstrumente")

        try:
            for einRundinstrument, einePosition in zip(self.meineRundinstrumente, self.einzelneRundinstrumentPositionen):
                einRundinstrument.update(einePosition[0], einePosition[1], einePosition[2], einePosition[3], self.allgemeinerRadius)
        except AttributeError:
            print("Beim Ersten Mal aufrufen können die einzelnen Rundinstrumente noch nicht geupdatet werden, da diese noch nicht existieren.")

    def updateSchatten(self, eingabeSchattenXoffset, eingabeSchattenYoffset):
        for einRundinstrument in self.meineRundinstrumente:
            einRundinstrument.updateSchatten(eingabeSchattenXoffset, eingabeSchattenYoffset)

    def delete(self):
        for einRundinstrument in self.meineRundinstrumente:
            einRundinstrument.delete()

    def zeichnen(self):
        for einRundinstrument in self.meineRundinstrumente:
            einRundinstrument.zeichnen()

    def updateAnzeige(self):
        for einRundinstrument in self.meineRundinstrumente:
            einRundinstrument.updateAnzeige()

    def setColorScheme(self, istTag):
        for einRundinstrument in self.meineRundinstrumente:
            einRundinstrument.setRundinstrumentColorScheme(istTag)


class Alarmanzeige:

    def __init__(self, eingabeRoot, eingabeCanvas, eingabeText, istTag):
        self.root = eingabeRoot
        self.meinCanvas = eingabeCanvas
        self.text = eingabeText
        self.font = "Piboto"
        self.fontSize = int(fontSizeFaktor*int(self.meinCanvas.winfo_height()/10))
        self.label = None

        self.farbeAlarmBackground = None
        self.farbeAlarmForeground = None

        if istTag:
            self.farbeAlarmBackground = "grey10"
            self.farbeAlarmForeground = "red"
        else:
            self.farbeAlarmBackground = "grey90"
            self.farbeAlarmForeground = "orange"

    def update(self, eingabeText):
        self.text = eingabeText

    def zeichnen(self):
        self.label = Label(
            self.root,
            text = self.text,
            bg = self.farbeAlarmBackground,
            fg = self.farbeAlarmForeground,
            font = (self.font, int(fontSizeFaktor*self.fontSize))
        )
        self.label.pack()
        self.label.place(
            x = self.meinCanvas.winfo_width()/2,
            y = self.meinCanvas.winfo_height()/2,
            anchor = "c"
        )

    def blinken(self):
        self.label.config(
            text = "",
        )
        time.sleep(0.5)
        self.label.config(
            text = self.text
        )

    def delete(self):
        self.label.destroy()


class App:
    def __init__(self, eingabeRoot, eingabeCanvas, eingabeUserName):

        # Farbvariablen
        self.Design = True
        self.farbeAppBackground = None
        self.farbeAppDock = None

        self.farbeWindowCanvasFrame = None

        self.farbeMesswertBackground = None
        self.farbeMesswertForeground = None

        self.farbeButtonForeground = None

        self.farbeCanvas = "#FFFFFF"

        self.farbeAlarmBackground = None
        self.farbeAlarmForeground = None

        self.userName = eingabeUserName
        
        self.meinConfigHandler = configFileHandler(self.userName)
        self.meinConfigHandler.configLesen()
        self.meinConfigHandler.modocConfigLesen()
        self.meinUSBhandler = usbDataHandler()

        self.root = eingabeRoot
        self.meinCanvas = eingabeCanvas

        # Minus fensterHoehenAbzug bei der Hoehe da zu Beginn irgendwann einmal die fensterHoehe um ein paar Pixel erhoeht wird, das aber nicht ausfindig gemacht werden kann. Irgendwann nach dem ersten self.root.update()
        self.meinCanvas.config(width = self.meinConfigHandler.appBestimmendeMasse["fensterBreite"], height = self.meinConfigHandler.appBestimmendeMasse["fensterHoehe"] - fensterHoehenAbzug)
        self.abstandZumRand = self.meinConfigHandler.appBestimmendeMasse["abstandZumRand"]

        self.dockHoehe = self.meinConfigHandler.appBestimmendeMasse["dockHoehe"]
        self.fensterBreiteAufteilungWertegruppenRundinstrumente = self.meinConfigHandler.appBestimmendeMasse["fensterBreiteAufteilungWertegruppenRundinstrumente"]
        self.fensterHoeheAufteilungWertegruppenRundinstrumente = self.meinConfigHandler.appBestimmendeMasse["fensterHoeheAufteilungWertegruppenRundinstrumente"]

        self.Glättung = self.meinConfigHandler.appBestimmendeMasse["glaettung"]

        self.MesswertObjekte = {
                                       #Name                    Einheit     MinMesswert MaxMesswert MinYWert    MaxYWert    Skalenmax   SkalenIncLabel  SkalenIncStrich IndexInDataStream   IstTagFarbe IstNachtFarbe   Glättung
            "Drehzahl" :    Messobjekt("Drehzahl",              "U/m",      0,          20000,      0,          20000,      20,         10,             21,             0,                  "#fb3a36",  "#F44336",      self.Glättung,          self),
            "Drehmoment" :  Messobjekt("Drehmoment",            "Ncm",      0,          400,        0,          400,        400,        10,             43,             1,                  "#9CCC65",  "#64DD17",      self.Glättung,          self),
            "Schub":        Messobjekt("Schub",                 "kg",       0,          3000,       0,          3000,       3000,       6,              34,             2,                  "#53b9ff",  "#448AFF",      self.Glättung,          self),
            "Leistung":     Messobjekt("Leistung",              "W",        0,          3000,       0,          3000,       3000,       6,              13,             3,                  "#ae00d3",  "#AA00FF",      self.Glättung,          self),
            "Gas":          Messobjekt("Gas",                   "%",        0,          100,        0,          100,        100,        10,             21,             4,                  "#F09B41",  "#FB8C00",      self.Glättung,          self),

            "Temp1":        Messobjekt("Temperatur 1",         "°C",        0,          400,        0,          300,        400,        16,             33,             9,                  "#e74173",  "#FF1744",      self.Glättung,          self),
            "Temp2":        Messobjekt("Temperatur 2",         "°C",        0,          400,        0,          300,        400,        16,             33,             10,                 "#B2D753",  "#00b407",      self.Glättung,          self),
            "Temp3":        Messobjekt("Temperatur 3",         "°C",        0,          400,        0,          300,        400,        16,             33,             11,                 "#82D7EC",  "#0091EA",      self.Glättung,          self),
            "Temp4":        Messobjekt("Temperatur 4",         "°C",        0,          400,        0,          300,        400,        16,             33,             12,                 "#64FFC0",  "#18ad88",      self.Glättung,          self),
            "Temp5":        Messobjekt("Temperatur 5",         "°C",        0,          400,        0,          300,        400,        16,             33,             42,                 "#F09B41",  "#FB8C00",      self.Glättung,          self),
            "Temp6":        Messobjekt("Temperatur 6",         "°C",        0,          400,        0,          300,        400,        16,             33,             43,                 "#FF5090",  "#E91E63",      self.Glättung,          self),
            "Temp7":        Messobjekt("Temperatur 7",         "°C",        0,          400,        0,          300,        400,        16,             33,             44,                 "#A070FF",  "#D500F9",      self.Glättung,          self),
            "Temp8":        Messobjekt("Temperatur 8",         "°C",        0,          400,        0,          300,        400,        16,             33,             45,                 "#ae00d3",  "#AA00FF",      self.Glättung,          self),

            "VCC":          Messobjekt("VCC",                   "V",        0,          20,         0,          20,         20,         16,             33,             27,                 "#00B0FF",  "#0091EA",      self.Glättung,          self),
            "TempCPU":      Messobjekt("TempCPU",               "°C",       0,          100,        0,          100,        100,        16,             33,             14,                 "#90A4AE",  "#455A64",      self.Glättung,          self),
            "arduvers":     Messobjekt("Arduino Version",       "",         0,          0,          0,          0,          0,          0,              0,              41,                 "#EEFF41",  "#ffff00",      self.Glättung,          self),
            "shutdown":     Messobjekt("shutdown",              "",         0,          0,          0,          0,          0,          0,              0,              35,                 "#000000",  "#000000",      self.Glättung,          self),
            "taste1":       Messobjekt("taste1",                "",         0,          0,          0,          0,          0,          0,              0,              36,                 "#000000",  "#000000",      self.Glättung,          self),
            "taste2":       Messobjekt("taste2",                "",         0,          0,          0,          0,          0,          0,              0,              37,                 "#000000",  "#000000",      self.Glättung,          self),
            "taste3":       Messobjekt("taste3",                "",         0,          0,          0,          0,          0,          0,              0,              38,                 "#000000",  "#000000",      self.Glättung,          self),
            "taste4":       Messobjekt("taste4",                "",         0,          0,          0,          0,          0,          0,              0,              39,                 "#000000",  "#000000",      self.Glättung,          self),
            #                                                                                                                           x,              y = a * x + (a-1)
        }

        self.meinRechteck = self.meinCanvas.create_rectangle(0,0, self.meinCanvas.winfo_width(), self.meinCanvas.winfo_height(), fill = self.farbeCanvas, width = 0)

        self.WertegruppeEingabeArray = []
        for key in self.meinConfigHandler.wertegruppe:
            self.WertegruppeEingabeArray = self.WertegruppeEingabeArray + [self.MesswertObjekte[key]]
        if logg: print(self.WertegruppeEingabeArray)

        self.eineWertegruppe = Wertegruppe(self.root, self.meinCanvas, 500, 1000, 0, 500,
            self.WertegruppeEingabeArray
        )

        self.eineWertegruppe.zeichnen()


        self.RundinstrumenteEingabeArray = []
        for key in self.meinConfigHandler.rundinstrumente:
            self.RundinstrumenteEingabeArray = self.RundinstrumenteEingabeArray + [self.MesswertObjekte[key]]

        #self, eingabeRoot, eingabeMessobjekt, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeRadius, eingabeSchattenXoffset, eingabeSchattenYoffset
        self.Rundinstrumente = RundinstrumentenGruppe(
            self.root,
            self.meinCanvas,
            self.RundinstrumenteEingabeArray,
            750,
            1900,
            500,
            900,
            self.meinConfigHandler.appBestimmendeMasse["rundinstrumentSchattenXoffset"],
            self.meinConfigHandler.appBestimmendeMasse["rundinstrumentSchattenYoffset"],
            5
        )

        self.Rundinstrumente.zeichnen()

        self.GraphenEingabeArray = []
        for keyArray in self.meinConfigHandler.graphen:
            eineNParray = np.array([])
            for key in keyArray:
                eineNParray = np.append(eineNParray, [self.MesswertObjekte[key]])
            self.GraphenEingabeArray = self.GraphenEingabeArray + [eineNParray]
        if logg: print(self.GraphenEingabeArray)

        self.Graphs = np.array([])

        for eineNParray in self.GraphenEingabeArray:
            self.Graphs = np.append(self.Graphs, [
                Graph(
                    self.meinCanvas,
                    self.abstandZumRand,
                    self.abstandZumRand+50,
                    self.meinCanvas.winfo_width()*0.5,
                    0,
                    500,
                    50,
                    eineNParray,
                    History
                ),
            ])


        self.dock = Dock(self.root, self, self.meinCanvas, self.dockHoehe, self.abstandZumRand)
        self.dock.zeichnen()

        if self.userName == "login":
            self.dock.userAnmeldung()

        for einGraph in self.Graphs:
            einGraph.zeichnen()

    def resizeCallback(self, event):
        self.guiReset()

    def guiReset(self):

        # Update der App-bestimmenden Masse
        self.meinConfigHandler.appBestimmendeMasse["fensterBreite"] = self.meinCanvas.winfo_width()
        self.meinConfigHandler.appBestimmendeMasse["fensterHoehe"] = self.meinCanvas.winfo_height()
        self.meinConfigHandler.appBestimmendeMasse["fensterBreiteAufteilungWertegruppenRundinstrumente"] = self.fensterBreiteAufteilungWertegruppenRundinstrumente
        self.meinConfigHandler.appBestimmendeMasse["fensterHoeheAufteilungWertegruppenRundinstrumente"] = self.fensterHoeheAufteilungWertegruppenRundinstrumente
        self.meinConfigHandler.appBestimmendeMasse["glaettung"] = self.Glättung
        if self.userName != "login":
            self.meinConfigHandler.configSchreiben()

        self.meinCanvas.delete(self.meinRechteck)
        self.meinRechteck = self.meinCanvas.create_rectangle(0,0, self.meinCanvas.winfo_width(), self.meinCanvas.winfo_height(), fill = self.farbeCanvas, width = 0)

        # Update Wertegruppe
        if self.eineWertegruppe.WertegruppenElemente.size > 0:
            self.eineWertegruppe.update(
                self.fensterBreiteAufteilungWertegruppenRundinstrumente*self.meinCanvas.winfo_width()*0.01+15,
                self.meinCanvas.winfo_width()-self.abstandZumRand,
                self.abstandZumRand+20,
                self.fensterHoeheAufteilungWertegruppenRundinstrumente*self.meinCanvas.winfo_height()*0.01-15,
            )
            self.eineWertegruppe.delete()
            self.eineWertegruppe.zeichnen()
            self.eineWertegruppe.updateAnzeige()



        # Update Graphen
        # Variable zur Bestimmung des Platzes entlang der Y-Achse pro Graphen
        if self.Graphs.size > 0:
            yPlatzProGraph = (self.meinCanvas.winfo_height() - self.abstandZumRand - self.dockHoehe - 20)/self.Graphs.size

            # Laufvariable zum Mitzählen der Graphen, wichtig zur Bestimmung der Positionierung der Graphen entlang der Y-Achse
            yLaufvariable = 0

            for einGraph in self.Graphs:
                einGraph.update(
                    self.abstandZumRand+50,
                    self.fensterBreiteAufteilungWertegruppenRundinstrumente*self.meinCanvas.winfo_width()*0.01,
                    self.abstandZumRand + yLaufvariable * yPlatzProGraph,
                    self.abstandZumRand + (yLaufvariable + 1) * yPlatzProGraph,
                    self.abstandZumRand,
                    History
                )
                einGraph.delete()
                einGraph.zeichnen()
                yLaufvariable = yLaufvariable + 1



        # Update Rundinstrumente
        if self.Rundinstrumente.meineRundinstrumente.size > 0:
            self.Rundinstrumente.update(
                self.fensterBreiteAufteilungWertegruppenRundinstrumente*self.meinCanvas.winfo_width()*0.01+15,
                self.meinCanvas.winfo_width()-self.abstandZumRand,
                self.fensterHoeheAufteilungWertegruppenRundinstrumente*self.meinCanvas.winfo_height()*0.01,
                self.meinCanvas.winfo_height()-self.dockHoehe - 20
            )
            self.Rundinstrumente.delete()
            self.Rundinstrumente.zeichnen()



        # Update Dock
        self.dock.update(self.dockHoehe, self.abstandZumRand)
        self.dock.delete()
        self.dock.zeichnen()

    def guiResetToConfigFile(self):

        self.meinCanvas.config(width = self.meinConfigHandler.appBestimmendeMasse["fensterBreite"], height = self.meinConfigHandler.appBestimmendeMasse["fensterHoehe"] - fensterHoehenAbzug)
        self.abstandZumRand = self.meinConfigHandler.appBestimmendeMasse["abstandZumRand"]

        self.dockHoehe = self.meinConfigHandler.appBestimmendeMasse["dockHoehe"]
        self.fensterBreiteAufteilungWertegruppenRundinstrumente = self.meinConfigHandler.appBestimmendeMasse["fensterBreiteAufteilungWertegruppenRundinstrumente"]
        self.fensterHoeheAufteilungWertegruppenRundinstrumente = self.meinConfigHandler.appBestimmendeMasse["fensterHoeheAufteilungWertegruppenRundinstrumente"]

        self.meinCanvas.delete(self.meinRechteck)
        self.meinRechteck = self.meinCanvas.create_rectangle(0,0, self.meinCanvas.winfo_width(), self.meinCanvas.winfo_height(), fill = self.farbeCanvas, width = 0)

        # Update Wertegruppe
        self.eineWertegruppe.update(
            self.fensterBreiteAufteilungWertegruppenRundinstrumente*self.meinCanvas.winfo_width()*0.01+15,
            self.meinCanvas.winfo_width()-self.abstandZumRand,
            self.abstandZumRand+20,
            self.fensterHoeheAufteilungWertegruppenRundinstrumente*self.meinCanvas.winfo_height()*0.01-15,
        )
        self.eineWertegruppe.delete()
        self.eineWertegruppe.zeichnen()
        self.eineWertegruppe.updateAnzeige()

        # Update Graphen
        for einGraph in self.Graphs:
            einGraph.update(
                self.abstandZumRand+50,
                self.fensterBreiteAufteilungWertegruppenRundinstrumente*self.meinCanvas.winfo_width()*0.01,
                self.abstandZumRand,
                self.meinCanvas.winfo_height() - self.dockHoehe - 20,
                self.abstandZumRand,
                History
            )
            einGraph.delete()
            einGraph.zeichnen()

        # Update Rundinstrumente
        self.Rundinstrumente.update(
            self.fensterBreiteAufteilungWertegruppenRundinstrumente*self.meinCanvas.winfo_width()*0.01+15,
            self.meinCanvas.winfo_width()-self.abstandZumRand,
            self.fensterHoeheAufteilungWertegruppenRundinstrumente*self.meinCanvas.winfo_height()*0.01,
            self.meinCanvas.winfo_height()-self.dockHoehe - 20
        )
        self.Rundinstrumente.updateSchatten(
            self.meinConfigHandler.appBestimmendeMasse["rundinstrumentSchattenXoffset"],
            self.meinConfigHandler.appBestimmendeMasse["rundinstrumentSchattenYoffset"],
        )
        self.Rundinstrumente.delete()
        self.Rundinstrumente.zeichnen()

        # Update Dock
        self.dock.update(self.dockHoehe, self.abstandZumRand)
        self.dock.delete()
        self.dock.zeichnen()


    def toggleColorScheme(self):
        self.Design = not self.Design
        for einGraph in self.Graphs:
            einGraph.setColorScheme(self.Design)
        self.Rundinstrumente.setColorScheme(self.Design)
        self.dock.setColorScheme(self.Design)
        self.eineWertegruppe.setWertegruppeColorScheme(self.Design)
        if self.Design:
            self.meinCanvas.config(bg = "#FFFFFF")
            self.farbeCanvas = "#FFFFFF"
        else:
            self.meinCanvas.config(bg = "#0a0a0a")
            self.farbeCanvas = "#0a0a0a"

        self.guiReset()

    def shutdownProzedur(self):
        self.shutdownAlarm = Alarmanzeige(
            self.root,
            self.meinCanvas,
            " Shutdown in 5 Sekunden ",
            self.Design
        )
        self.shutdownAlarm.zeichnen()

        self.root.update()
        # time.sleep(0.5)
        time.sleep(1)

        for i in range(-4, 0):
            self.shutdownAlarm.update(" Shutdown in " + str(-i) + " Sekunden ")
            self.shutdownAlarm.delete()
            self.shutdownAlarm.zeichnen()
            self.root.update()
            time.sleep(1)

        if platform.system() == 'Darwin':
            self.root.destroy()
        else:
            # Shutdown Command ist schon im Dock implementiert, daher wird auch diese aufgerufen
            self.dock.shutdownCommand()

    def restartWegenLowSamplingRateProzedur(self):
        self.shutdownAlarm = Alarmanzeige(
            self.root,
            self.meinCanvas,
            " Low Sampling Rate - Restart in 5 Sekunden ",
            self.Design
        )
        self.shutdownAlarm.zeichnen()

        self.root.update()
        time.sleep(1)

        for i in range(-4, 0):
            self.shutdownAlarm.update(" Low Sampling Rate - Restart in " + str(-i) + " Sekunden ")
            self.shutdownAlarm.delete()
            self.shutdownAlarm.zeichnen()
            self.root.update()
            time.sleep(1)

        self.dock.restartCommand()


    def appLoop(self):

        lasttime = time.time()
        time.sleep(0.1)
        self.sampleRateArray = np.array([])

        while True:

            # Berechnen und Anzeigen der Sampling Rate (mit Glättung)
            sampleRate = 1/(float(time.time() - lasttime))
            lasttime = time.time()
            #self.dock.updateSamplingAnzeige(sampleRate) # Entkommentieren wenn ungeglättete Sampling-Rate angzeigt werden soll
            self.sampleRateArray = np.append(self.sampleRateArray, [sampleRate])
            self.sampleRateArrayMean = np.mean(self.sampleRateArray)
            if(self.sampleRateArray.size > 20):
                self.sampleRateArray = np.delete(self.sampleRateArray, 0)
            try:
                self.dock.updateSamplingAnzeige(self.sampleRateArrayMean)
            except:
                print("Kann Sampling Anzeige nicht updaten")

            # Überprüfen ob die durchschnittliche Sampling Rate geringer als 1 ist
            if(self.sampleRateArrayMean < 1):
                if(self.sampleRateArray.size > 10):
                    self.restartWegenLowSamplingRateProzedur()


            # Hier rufen alle Messwert Objekt ihren aktuellen Wert aus dem Data Stream ab
            abfangenReturnValue = self.meinUSBhandler.leseUSBline()
            for key in self.MesswertObjekte:
                self.MesswertObjekte[key].refreshYourValue(self.meinUSBhandler.data, self.meinConfigHandler.modocKonstanten)

            # Ueberpruefen auf Shutdown Command von Arduino
            if self.MesswertObjekte["shutdown"].value == 0:
                self.shutdownProzedur()

            if self.dock.aktiveAnmeldung:
                # Tasten sollen hier fuer Auswahl des Benutzers verwendet werden
                if self.MesswertObjekte["taste1"].value == 0:                   # Nach Oben
                    self.dock.anmeldeFensterNachOben()
                if self.MesswertObjekte["taste2"].value == 0:                   # Nach Unten
                    self.dock.anmeldeFensterNachUnten()
                if self.MesswertObjekte["taste3"].value == 0:                   # Auswaehlen
                    self.dock.userAnmeldungFortsetzung()
                if (self.MesswertObjekte["taste4"].value == 0) & (self.userName != "login"):                   # Abbrechen
                    self.dock.userAnmeldungAbbrechen()
            elif self.dock.aktivesMenu:
                # Tasten sollen hier fuer Auswahl eines Menupunkts verwendet werden
                if self.MesswertObjekte["taste1"].value == 0:                   # Nach Oben
                    self.dock.menuFensterNachOben()
                if self.MesswertObjekte["taste2"].value == 0:                   # Nach Unten
                    self.dock.menuFensterNachUnten()
                if self.MesswertObjekte["taste3"].value == 0:                   # Auswaehlen
                    self.dock.menuFortsetzung()
            elif self.dock.aktiverKalibrierungsvorgang:
                if self.MesswertObjekte["taste1"].value == 0:
                    self.dock.eigentlicheKalibrieren()
                if self.MesswertObjekte["taste4"].value == 0:
                    self.dock.kalibrierenEnde()
            elif self.dock.aktiverKalibrierungsvorgangFortsetzung:
                if self.MesswertObjekte["taste4"].value == 0:
                    self.dock.kalibrierenEnde()
            elif self.dock.aktiveGlaettungsAenderung:
                if self.MesswertObjekte["taste1"].value == 0:                   # Nach Oben
                    self.dock.glaettungsFensterRauf()
                if self.MesswertObjekte["taste2"].value == 0:                   # Nach Unten
                    self.dock.glaettungsFensterRunter()
                if self.MesswertObjekte["taste3"].value == 0:                   # Auswaehlen
                    self.dock.glaettungsFensterFortsetzung()
                if self.MesswertObjekte["taste4"].value == 0:                   # Abbruch
                    self.dock.glaettungsAenderungAbbruch()
            elif self.dock.aktiveAenderungHorizontaleTeilung:
                if self.MesswertObjekte["taste1"].value == 0:                   # Nach Links
                    self.dock.horizontaleTeilungNachLinks()
                if self.MesswertObjekte["taste2"].value == 0:                   # Nach Rechts
                    self.dock.horizontaleTeilungNachRechts()
                if self.MesswertObjekte["taste3"].value == 0:                   # Auswaehlen
                    self.dock.horizontaleTeilungFensterDelete()
                if self.MesswertObjekte["taste4"].value == 0:                   # Abbruch
                    self.dock.horizontaleTeilungFensterAbbruch()
            elif self.dock.aktiveAenderungVertikaleTeilung:
                if self.MesswertObjekte["taste1"].value == 0:                   # Nach Links
                    self.dock.vertikaleTeilungNachLinks()
                if self.MesswertObjekte["taste2"].value == 0:                   # Nach Rechts
                    self.dock.vertikaleTeilungNachRechts()
                if self.MesswertObjekte["taste3"].value == 0:                   # Auswaehlen
                    self.dock.vertikaleTeilungFensterDelete()
                if self.MesswertObjekte["taste4"].value == 0:                   # Abbruch
                    self.dock.vertikaleTeilungFensterAbbruch()
            else:
                # Tasten sollen hier nach dem üblichen Schema verwendet werden
                if self.MesswertObjekte["taste1"].value == 0:                   # Menu Aufbau
                    self.dock.menuFensterAufbau()
                if self.MesswertObjekte["taste2"].value == 0:                   # Screenshot ausloesen
                    self.dock.screenshotAusloesen()


            self.eineWertegruppe.updateAnzeige()

            self.Rundinstrumente.updateAnzeige()

            for einGraph in self.Graphs:
                einGraph.updateAnzeige()

            self.root.update()


class configFileHandler:

    def __init__(self, eingabeUsername):

        self.appBestimmendeMasse = {
            "fensterBreite" : 1900,
            "fensterHoehe" : 1000,
            "fensterBreiteAufteilungWertegruppenRundinstrumente" : 40,
            "fensterHoeheAufteilungWertegruppenRundinstrumente" : 50,
            "abstandZumRand" : 100,
            "dockHoehe" : 100,
            "rundinstrumentSchattenXoffset" : 1,
            "rundinstrumentSchattenYoffset" : 1,
            "glaettung": 10,
            "Rundinstrumente" : "Temp1",
            "Graphen" : "Temp1",
            "Wertegruppe" : "Temp1"
        }

        self.rundinstrumente = []
        self.graphen = []
        self.wertegruppe = []

        self.modocKonstanten = {
            "upm_eich1" : 3011100,
            "upm_eich2" : 1150,
            "upm_eich3" : -69,
            "drehmoment_eich1" : 650,
            "drehmoment_eich2" : -26652,
            "schub_eich1" : 1160,
            "schub_eich2" : 4932,
            "vccspannung_eich1" : 61,
            "vccspannung_eich2" : 0,
            "temp_eich1" : 0,
            "temp_eich2" : 0,
            "temp_eich3" : 0,
            "temp_eich4" : 0,
            "temp_eich5" : 0,
            "temp_eich6" : 0,
            "temp_eich7" : 0,
            "temp_eich8" : 0,
            "drehmoment_kal" : 0,
            "schub_kal" : 0,
        }
        self.setUserName(eingabeUsername)

    def setUserName(self, eingabeUserName):
        self.username = eingabeUserName

        if istPruefstand:
            self.modocConfigfilename = "modoc_conf.csv"
        else:
            self.modocConfigfilename = "makerbeam_conf.csv"

        if rasp  == 1:
            # self.configfilename = "/home/sp/config_" + self.username + ".csv"
            # self.modocConfigfilename = "/home/sp/" + self.modocConfigfilename
            self.configfilename = "config_" + self.username + ".csv"
            self.modocConfigfilename = "" + self.modocConfigfilename
        else:
            self.configfilename = "config_" + self.username + ".csv"


    def configLesen(self):
        ####################################################################################
        ### Lese Variable aus Configfile config_USER.csv / im Problemfall setze Defaultwerte
        ####################################################################################

        configfile = None

        try:
            configfile = csv.reader(open(self.configfilename, "r"), delimiter=";")
        except FileNotFoundError:
            print ("Configfile: ", self.configfilename, " nicht gefunden!")

        configIdentifier = np.array([])
        configValue = np.array([])
        AccessIndex = 0
        istFehlerfrei = True

        if configfile != None:
            for zeile in configfile:
                    configIdentifier = np.append(configIdentifier, zeile[0])
                    configValue = np.append(configValue, zeile[1])

            for identifier, value in self.appBestimmendeMasse.items():

                if(configIdentifier[AccessIndex] == identifier):

                    if (identifier == "Rundinstrumente"):
                        self.appBestimmendeMasse[identifier] = configValue[AccessIndex]
                        for element in csv.reader([configValue[AccessIndex]], delimiter = "/"):
                            self.rundinstrumente = self.rundinstrumente + element

                    elif (identifier == "Graphen"):
                        self.appBestimmendeMasse[identifier] = configValue[AccessIndex]
                        for element in csv.reader([configValue[AccessIndex]], delimiter = "/"):
                            for unterelement in csv.reader(element, delimiter = ","):
                                self.graphen = self.graphen + [unterelement]

                    elif (identifier == "Wertegruppe"):
                        self.appBestimmendeMasse[identifier] = configValue[AccessIndex]
                        for element in csv.reader([configValue[AccessIndex]], delimiter = "/"):
                            self.wertegruppe = self.wertegruppe + element

                    else:
                        self.appBestimmendeMasse[identifier] = int(configValue[AccessIndex])
                else:
                    print("Falscher Inhalt in ", identifier, " : ", configIdentifier[AccessIndex])
                    istFehlerfrei = False
                AccessIndex = AccessIndex + 1
        else:
            istFehlerfrei = False

        if(not istFehlerfrei):
            print("Fehlerhaftes Configfile " + self.configfilename + " daher Defaultwerte verwenden")

    def configSchreiben(self):

        #######################################################
        ### Schreibe Variable ins Configfile config_USER.csv
        #######################################################
        print("Schreiben des configfiles:" + self.configfilename)

        try:
            configfile = csv.writer(open(self.configfilename, "w"), delimiter=";")
        except FileNotFoundError:
            print ("Configfile: ", configfilename, " kann nicht geschrieben werden")

        configDaten = (
            ["fensterBreite", self.appBestimmendeMasse["fensterBreite"]],
            ["fensterHoehe", self.appBestimmendeMasse["fensterHoehe"]],
            ["fensterBreiteAufteilungWertegruppenRundinstrumente", self.appBestimmendeMasse["fensterBreiteAufteilungWertegruppenRundinstrumente"]],
            ["fensterHoeheAufteilungWertegruppenRundinstrumente", self.appBestimmendeMasse["fensterHoeheAufteilungWertegruppenRundinstrumente"]],
            ["abstandZumRand", self.appBestimmendeMasse["abstandZumRand"]],
            ["dockHoehe", self.appBestimmendeMasse["dockHoehe"]],
            ["rundinstrumentSchattenXoffset", self.appBestimmendeMasse["rundinstrumentSchattenXoffset"]],
            ["rundinstrumentSchattenYoffset", self.appBestimmendeMasse["rundinstrumentSchattenYoffset"]],
            ["glaettung", self.appBestimmendeMasse["glaettung"]],
            ["Rundinstrumente", self.appBestimmendeMasse["Rundinstrumente"]],
            ["Graphen", self.appBestimmendeMasse["Graphen"]],
            ["Wertegruppe", self.appBestimmendeMasse["Wertegruppe"]]
        )

        configfile.writerows(configDaten)
        print ("Configfile: ", self.configfilename, " schreiben OK")

    def modocConfigLesen(self):
        ####################################################################################
        ### Lese Variable aus Configfile modoc_conf.csv / im Problemfall setze Defaultwerte
        ### Alternativ gibts das makerbeam_conf.csv ... für den Makerbeam-Teststand
        ####################################################################################
        try:
            modocConfigfile = csv.reader(open(self.modocConfigfilename, "r"), delimiter=";")
        except FileNotFoundError:
            print ("ModocConfigfile: ", self.modocConfigfilename, " nicht gefunden!")

        configIdentifier = np.array([])
        configValue = np.array([])

        for zeile in modocConfigfile:
            configIdentifier = np.append(configIdentifier, zeile[0])
            configValue = np.append(configValue, zeile[1])

        AccessIndex = 0
        istFehlerfrei = True

        for identifier, value in self.modocKonstanten.items():
            if(configIdentifier[AccessIndex] == identifier):
                self.modocKonstanten[identifier] = int(configValue[AccessIndex])
            else:
                print("Falscher Inhalt in ", identifier, " : ", configIdentifier[AccessIndex])
                istFehlerfrei = False
            AccessIndex = AccessIndex + 1

        if(not istFehlerfrei):
            print("Fehlerhaftes ModocConfigfile " + self.configfilename + " daher Defaultwerte verwenden")

    def modocConfigSchreiben(self):
        ####################################################################################
        ### Schreibe Variable ins Configfile modoc_conf.csv / im Problemfall setze Defaultwerte
        ### Alternativ gibts das makerbeam_conf.csv ... für den Makterbeam-Teststand
        ####################################################################################

        try:
            modocConfigfile = csv.writer(open(self.modocConfigfilename, "w"), delimiter=";")
        except FileNotFoundError:
            print ("ModocConfigfile: ", self.modocConfigfilename, " nicht gefunden!")

        modocConfigDaten = (
            ["upm_eich1", self.modocKonstanten["upm_eich1"]],
            ["upm_eich2", self.modocKonstanten["upm_eich2"]],
            ["upm_eich3", self.modocKonstanten["upm_eich3"]],
            ["drehmoment_eich1", self.modocKonstanten["drehmoment_eich1"]],
            ["drehmoment_eich2", self.modocKonstanten["drehmoment_eich2"]],
            ["schub_eich1", self.modocKonstanten["schub_eich1"]],
            ["schub_eich2", self.modocKonstanten["schub_eich2"]],
            ["vccspannung_eich1", self.modocKonstanten["vccspannung_eich1"]],
            ["vccspannung_eich2", self.modocKonstanten["vccspannung_eich2"]],
            ["temp_eich1", self.modocKonstanten["temp_eich1"]],
            ["temp_eich2", self.modocKonstanten["temp_eich2"]],
            ["temp_eich3", self.modocKonstanten["temp_eich3"]],
            ["temp_eich4", self.modocKonstanten["temp_eich4"]],
            ["temp_eich5", self.modocKonstanten["temp_eich5"]],
            ["temp_eich6", self.modocKonstanten["temp_eich6"]],
            ["temp_eich7", self.modocKonstanten["temp_eich7"]],
            ["temp_eich8", self.modocKonstanten["temp_eich8"]],
            ["drehmoment_kal", self.modocKonstanten["drehmoment_kal"]],
            ["schub_kal", self.modocKonstanten["schub_kal"]]
        )

        modocConfigfile.writerows(modocConfigDaten)
        print ("Configfile: ", self.modocConfigfilename, " schreiben OK")


class usbDataHandler:

    def __init__(self):
        self.data = np.array([])
        self.istFehlerfrei = True

        self.sim0 = 10
        self.sim1 = 600
        self.simtemp8counter = 0
        self.simtemp8 = 0
        self.simtobi = 1

        self.taste1Value = 1
        self.taste2Value = 1
        self.taste3Value = 1
        self.taste4Value = 1

        if rasp:
            self.serialPort = '/dev/ttyACM0'
        else:
            self.serialPort = '/dev/tty.usbmodem1411'

        if (not usbsim):
            GPIO.output(11, GPIO.HIGH)
            USBwaitForResponse = True
            while USBwaitForResponse:
                try:
                    self.serialConnection = serial.Serial(self.serialPort)
                    USBwaitForResponse = False
                except:
                    print("Keine Antwort von Arduino")
                    time.sleep(1)

    # Fuer Tastatur Bedinung
    def taste1Tastatur(self, event = None):
        self.taste1Value = 0

    def taste2Tastatur(self, event = None):
        self.taste2Value = 0

    def taste3Tastatur(self, event = None):
        self.taste3Value = 0

    def taste4Tastatur(self, event = None):
        self.taste4Value = 0


    def leseUSBline(self):

        self.istFehlerfrei = True
        backup = self.data
        self.data = np.array([])

        if usbsim:

            self.sim1 = self.sim1 + random.randint(-150,150)
            if self.sim1 < 10:
                self.sim1 = 800
            if self.sim1 > 1100:
                self.sim1 = 300
            i = random.randint(0,200)

            self.simtemp8counter = self.simtemp8counter + 1     # damit man einen Graphen hat, der ausserhalb des Messbereichs läuft
            #self.simtemp8 = max (323, self.simtemp8)
            self.simtemp8 = 200*math.sin(math.pi/360*self.simtemp8counter)+200

            if self.simtemp8counter > 80:
                shutdown = 0
            else:
                shutdown = 1


            if (self.simtobi % 1000 == 0):
                simtobiValue = 400000
                self.simtobi-=1
            else:
                simtobiValue = 250000

            sim = np.array([
                random.randint(50000, 100000),    # 0 Drehzahl
                #9000000+ random.randint(0, 10000),               # 1
                #6000000+random.randint(0, 10000),          #2 Schub
                simtobiValue,
                400000,
                random.randint(10000, 20000), #3
                random.randint(0, 100), #4 Gas
                random.randint(0, 1), #5
                random.randint(40,90), #6
                random.randint(100,130), #7
                random.randint(120,150), #8
                random.randint(300,380),    #  9    das sind Werte für einen größeren Temperaturbereich
                random.randint(323,340),    # 10    das sind ADC Werte für 30oC bis  43oC
                random.randint(323,340),    # 11    das sind ADC Werte für 30oC bis  43oC
                random.randint(323,340),    # 12    das sind ADC Werte für 30oC bis  43oC
                0,0,0,0,0,0,0,              # 13..19
                0,0,0,0,0,0,0,0,0,0,        # 20..29
                0,0,0,0,0,                  # 30..34
                #shutdown,                  # 35
                1,                          # 35
                self.taste1Value,self.taste2Value,self.taste3Value,self.taste4Value,                    # 36..39
                0,9.0,                        # 40..41
                random.randint(323,340),    # 42    das sind ADC Werte für 30oC bis  43oC
                random.randint(323,340),    # 43    das sind ADC Werte für 30oC bis  43oC
                random.randint(323,340),    # 44    das sind ADC Werte für 30oC bis  43oC
                self.simtemp8    # 45    Testalternative für temp8: laufend steigernder Wert, der ausserhalb des Messbereichs läuft (siehe oben +1) geht aber erst hoch bei 323
            ])
            self.data = sim
            if self.sim0<200:
                self.sim0 += 5
            else:
                self.sim0 += 10
            if self.sim0 > 1000:
                self.sim0= 100

            if self.taste1Value == 0:
                self.taste1Value = 1
            if self.taste2Value == 0:
                self.taste2Value = 1
            if self.taste3Value == 0:
                self.taste3Value = 1
            if self.taste4Value == 0:
                self.taste4Value = 1

            time.sleep(0.025)
            self.simtobi += 1


        else:

            try:
                self.istFehlerfrei = True
                eineUSBlinie = self.serialConnection.readline().decode()
                dataStream = eineUSBlinie.split(';')

                for element in dataStream:
                    if element == '':
                        self.istFehlerfrei = False
                        print("USB DataStream Fehler: Leeres Feld  "  + str(time.strftime("%H:%M:%S", time.localtime(time.time()))))

                if len(dataStream) != 48:
                    self.istFehlerfrei = False
                    print("USB DataStream Fehler: Länge ist " + str(len(dataStream)) + "  " + str(time.strftime("%H:%M:%S", time.localtime(time.time()))))
                else:
                    if dataStream[46] != 'End':
                        self.istFehlerfrei = False
                        print("USB DataStream Fehler: Feld 46 nicht End, sondern: " + dataStream[46] + "  " + str(time.strftime("%H:%M:%S", time.localtime(time.time()))))

                if self.istFehlerfrei:
                    for element in dataStream:
                        if element == '' or element == 'End' or element == '\r\n':
                            element = '0'
                        self.data = np.append(self.data, abs(int(element)))

            except serial.serialutil.SerialException:
                self.istFehlerfrei = False
                print("USB DataStream Fehler: SerialException - Schlafe fuer 1 Sekunde  " + str(time.strftime("%H:%M:%S", time.localtime(time.time()))))
                time.sleep(1)
            except:
                self.istFehlerfrei = False
                print("USB DataStream Fehler: Unbekannter Fehler  " + str(time.strftime("%H:%M:%S", time.localtime(time.time()))))

            if (not self.istFehlerfrei):
                if backup.size != 48:
                        self.data = np.array([0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0])
                else:
                        self.data = backup

        return self.istFehlerfrei


root = Tk()
root.title("MoDoc '20 TOBI-Edition")
root.minsize(1440, 500)
windowCanvas = Canvas(root, width=1600, height=1000)
windowCanvas.pack(fill=BOTH, expand=YES)

userName = "login"

print(sys.argv)

if len(sys.argv) > 1:
    if os.path.isfile('config_' + sys.argv[-1] + '.csv'):
        userName =  sys.argv[-1]
    else:
        userName = "login"

app = App(root, windowCanvas, userName)

if usbsim:
    root.bind("1", app.meinUSBhandler.taste1Tastatur)
    root.bind("2", app.meinUSBhandler.taste2Tastatur)
    root.bind("3", app.meinUSBhandler.taste3Tastatur)
    root.bind("4", app.meinUSBhandler.taste4Tastatur)

windowCanvas.bind("<Configure>", app.resizeCallback)
windowCanvas.pack(fill=BOTH, expand=YES)
app.appLoop()
