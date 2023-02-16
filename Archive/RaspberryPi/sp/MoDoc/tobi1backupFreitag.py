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

# Fragen:
# Was macht Skalenmax, SkalenINcLabel, SkalenIncStrich?

# Schalter
rasp = 0
usbsim = 1
adcdirekt = 0
istPruefstand = 1
fontsizefaktor = 1
EH_Schub = 1
grLinienDicke = 1
grXsampling = 10

# Allgemeine Funktionen

######################################################################
### Aufrunden der Hilfslinienwerte auf gut lesbare 1.. / 2.. / 5.. Zahlen
### zb aus 234 wird 500      aus 66 wird 100
######################################################################
def Aufrunden125(input):

    if input < 1:
        ru125 = 1
        #        print ("Aufrunden ", input, ru125)
    else:
        loginput = int(math.log10(input))       # bei input 456 -> loginput = 2 (10 hoch 2)
        wertinput = input / 10**loginput
        normierung = 1
        if wertinput > 5: normierung = 10
        else:
            if wertinput > 2: normierung = 5
            else:
                if wertinput > 1: normierung = 2
        ru125 = normierung * 10**loginput
        #        print ("Aufrunden ", input, loginput, wertinput, normierung, ru125)

    return ru125

def Abrunden125(input):     # Abrunden auf 1 / 2 / 5 zu Beginn

    if input < 1:
        ru125 = 1
    else:
        loginput = int(math.log10(input))       # bei input 456 -> loginput = 2 (10 hoch 2)
        wertinput = input / 10**loginput
        normierung = 1
        if wertinput > 5: normierung = 5
        else:
            if wertinput > 2: normierung = 2
            else:
                if wertinput > 1: normierung = 1
        ru125 = normierung * 10**loginput

    return ru125

def Abrunden2te05(input):     # Abrunden der 2ten Stelle auf 0 oder 5 (12->10 765->750)

    if input < 5:
        ru2te05 = 0
    else:
        if input < 10:
            ru2te05 = 5
        else:
            loginput = int(math.log10(input))       # bei input 456 -> loginput = 2 (10 hoch 2)
            erstestelle = int(input / 10**loginput)
            zweitestelle = int((input - erstestelle * 10**loginput) / 10**(loginput-1))
            if zweitestelle > 5:
                zweitestelle = 5
            else:
                zweitestelle = 0
            ru2te05 = erstestelle * 10**loginput + zweitestelle * 10**(loginput-1)
            #    print ("Abrunden2te105 ", input, ru2te05)
    return ru2te05

def Luminance(eingabeHexFarbe):
    red = int(eingabeHexFarbe[1 : 3], 16)
    blue = int(eingabeHexFarbe[3 : 5], 16)
    green = int(eingabeHexFarbe[5 : 7], 16)
    #if (0.2126*red + 0.7152*green + 0.0722*blue) > 50:
    #print(math.sqrt( 0.299*pow(red,2) + 0.587*pow(green,2) + 0.114*pow(blue,2) ))
    # print(0.299*red + 0.587*green + 0.114*blue)
    if (math.sqrt( 0.299*pow(red,2) + 0.587*pow(green,2) + 0.114*pow(blue,2) )) > 200:
        return "#000000"
    else:
        return "#ffffff"



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
        e = dig         # Direkt für Tests und Eichung den ADC Wert (0..1023) anzeigen

    return e

class Messobjekt:

    def __init__(self, eingabeMesswertName, eingabeMesswertEinheit, eingabeMinimalerMesswert, eingabeMaximalerMesswert, eingabeMinimalerYachsenWert, eingabeMaximalerYachsenWert, eingabeSkalenmax, eingabeSkalenIncLabel, eingabeSkalenIncStrich, eingabeIndexInDataStream, eingabeIstTagFarbe, eingabeIstNachtFarbe):

        self.MesswertName = eingabeMesswertName
        self.MesswertEinheit = eingabeMesswertEinheit

        self.MinimalerMesswert = eingabeMinimalerMesswert
        self.MaximalerMesswert = eingabeMaximalerMesswert

        self.MinimalerYachsenWert = eingabeMinimalerYachsenWert
        self.MaximalerYachsenWert = eingabeMaximalerYachsenWert

        self.Skalenmax = eingabeSkalenmax
        self.SkalenIncLabel = eingabeSkalenIncLabel
        self.SkalenIncStrich = eingabeSkalenIncStrich

        self.IndexInDataStream = eingabeIndexInDataStream

        self.istTagFarbe = eingabeIstTagFarbe
        self.istNachtFarbe = eingabeIstNachtFarbe

        self.value = 0
        self.ringbuffer = np.array([])

    def refreshYourValue(self, eingabeDataStream, eingabeModocKonstanten):
        if self.IndexInDataStream < 5:
            if self.IndexInDataStream == 0: # Drehzahl
                if eingabeDataStream[self.IndexInDataStream] > 0:
                    self.value = int((eingabeModocKonstanten["upm_eich1"] + (eingabeModocKonstanten["upm_eich2"] - eingabeDataStream[self.IndexInDataStream]) * eingabeModocKonstanten["upm_eich3"]) / eingabeDataStream[self.IndexInDataStream])         # Eichung UPM in 1/min

            if self.IndexInDataStream == 1: # Drehmoment
                self.value = int(eingabeDataStream[self.IndexInDataStream] / eingabeModocKonstanten["drehmoment_eich1"] - eingabeModocKonstanten["drehmoment_eich2"]) + eingabeModocKonstanten["drehmoment_kal"]

            if self.IndexInDataStream == 2: # Schub
                self.value = int((eingabeDataStream[self.IndexInDataStream] / eingabeModocKonstanten["schub_eich1"] - eingabeModocKonstanten["schub_eich2"]) * EH_Schub)
            if self.IndexInDataStream == 3: # Leistung
                self.value = int(2 * math.pi * eingabeDataStream[1]/100 * eingabeDataStream[0]/60)
            if self.IndexInDataStream == 4: # Gas (Wird vorlaeufig auf Null gesetzt)
                self.value = 0

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
                if rasp == 1:
                    tempFile = open ("/sys/class/thermal/thermal_zone0/temp")
                    self.value = tempFile.read()
                    tempFile.close()
                    self.value = int(float(self.value)/1000)
                else:
                    self.value = 99

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


class Rundinstrument:

    def __init__(self, eingabeRoot, eingabeMessobjekt, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeRadius, eingabeSchattenXoffset, eingabeSchattenYoffset):

        self.root = eingabeRoot
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
        self.LabelText = "Hallo"

        self.winkelHilfe = math.pi*0.2

        self.SkalenLabel = np.array([])
        self.dieLinien = np.array([])

    def update(self, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeRadius):
        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2
        self.radius = eingabeRadius

        self.mittelpunktX = self.posX1 + (self.posX2-self.posX1)/2
        self.mittelpunktY = self.posY1 + (self.posY2-self.posY1)/2

        self.zeigerKreisRadius = max(self.radius/10, 10)
        self.graueFlächeRadius = max(self.radius/50,5)

        # "Anfang" und "Ende" im Sinne von Zeichnen der Striche von Außen nach Innen
        self.strichAnfangDistanzRand = max(self.radius/30, 5)
        self.strichEndeDistanzRand = max(self.radius/7, 2)

        self.zeigerLaenge = self.radius-self.strichEndeDistanzRand
        self.zeigerBreite = max(self.zeigerLaenge/20, 10)


    def setRundinstrumentColorScheme(self, istTag):
        if istTag:
            self.farbeRundinstrumentBackground = "grey90"
            self.farbeRundinstrumentRahmen = "red"
            self.farbeRundinstrumentLabel = "grey10"
            self.farbeRundinstrumentSchatten = "grey70"
            self.farbeRundinstrumentLinie = "grey30"
            self.farbeRundinstrumentZeiger = "red"

            self.farbeRundinstrumentLabelBackground = self.meinMessobjekt.istTagFarbe


        else:
            self.farbeRundinstrumentBackground = "grey5"
            self.farbeRundinstrumentRahmen = "firebrick"
            self.farbeRundinstrumentLabel = "grey99"
            self.farbeRundinstrumentSchatten = "grey15"
            self.farbeRundinstrumentLinie = "grey70"
            self.farbeRundinstrumentZeiger = "firebrick"

            self.farbeRundinstrumentLabelBackground = self.meinMessobjekt.istNachtFarbe

        self.farbeRundinstrumentLabelForeground = Luminance(self.farbeRundinstrumentLabelBackground)

    def zeichnen(self):

        self.derRoteRahmen = windowCanvas.create_oval(
            self.posX1,
            self.posY1,
            self.posX2,
            self.posY2,
            fill = self.farbeRundinstrumentRahmen
        )

        self.dieGraueFläche = windowCanvas.create_oval(
            self.posX1 + self.graueFlächeRadius,
            self.posY1 + self.graueFlächeRadius,
            self.posX2 - self.graueFlächeRadius,
            self.posY2 - self.graueFlächeRadius,
            fill = self.farbeRundinstrumentBackground
        )

        self.EinLabelWert = Label(
            self.root,
            text = self.LabelText,
            bg = self.farbeRundinstrumentLabelBackground,
            fg = self.farbeRundinstrumentLabelForeground,
            font = ("fixedsys", max(int(self.radius/8),10))
        )
        self.EinLabelWert.pack()
        self.EinLabelWert.place(
            x = self.mittelpunktX,
            y = self.mittelpunktY + self.radius * 0.4,
            anchor="c"
        )

        self.EinLabelWert2 = Label(
            self.root,
            text = self.LabelText,
            bg = self.farbeRundinstrumentLabelBackground,
            fg = self.farbeRundinstrumentLabelForeground,
            font = ("fixedsys", max(int(self.radius/8),10))
        )
        self.EinLabelWert2.pack()
        self.EinLabelWert2.place(
            x = self.mittelpunktX,
            y = self.mittelpunktY - self.radius * 0.4,
            anchor="c"
        )

        self.SkalenLabel = np.array([])
        self.dieLinien = np.array([])
        self.winkelHilfe = math.pi*0.2

        i = 0;
        labinc = (self.meinMessobjekt.Skalenmax - self.meinMessobjekt.MinimalerMesswert)/self.meinMessobjekt.SkalenIncLabel
        while (self.winkelHilfe <= math.pi * 1.9):

            self.SkalenLabel = np.append(self.SkalenLabel,[Label(
                root,
                text = self.LabelText,
                bg = self.farbeRundinstrumentBackground,
                fg = self.farbeRundinstrumentLabel,
                font = ("fixedsys", max(int(self.radius/12),2))
            )])

            self.SkalenLabel[i].pack()
            self.SkalenLabel[i].place(
                x = self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichEndeDistanzRand * 1.5),
                y = self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichEndeDistanzRand * 1.5),
                anchor="c"
            )

            lab = self.meinMessobjekt.MinimalerMesswert + labinc * i

            self.SkalenLabel[i].config(text = str(int(lab)))


            self.dieLinien = np.append(self.dieLinien, [windowCanvas.create_line(
                self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichEndeDistanzRand*0.7),
                self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichEndeDistanzRand*0.7),
                self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichAnfangDistanzRand),
                self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichAnfangDistanzRand),
                fill=self.farbeRundinstrumentLinie,
                width=max(int(self.radius/60),2)
            )])

            self.dieLinien = np.append(self.dieLinien, [windowCanvas.create_line(
                self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichEndeDistanzRand * 1.5),
                self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichEndeDistanzRand * 1.5),
                self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichAnfangDistanzRand),
                self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.radius - self.strichAnfangDistanzRand),
                fill=self.farbeRundinstrumentLinie,
                width=max(int(self.radius/60),2)
            )])

            self.winkelHilfe = self.winkelHilfe + math.pi*1.8/(self.meinMessobjekt.SkalenIncLabel+1)
            i += 1


        self.zeichneBewegicheTeile()

        self.EinLabelWert.config(text = "Hallo" + " " + self.einheit)
        self.EinLabelWert2.config(text = self.name)

    def delete(self):

        windowCanvas.delete(self.derRoteRahmen)
        windowCanvas.delete(self.dieGraueFläche)
        self.EinLabelWert.destroy()
        self.EinLabelWert2.destroy()

        for Linie in np.nditer(self.dieLinien):
            windowCanvas.delete(int(Linie))

        for i in range(0, self.SkalenLabel.size):
            self.SkalenLabel[i].destroy()

        windowCanvas.delete(self.zeigerKreisSchatten)
        windowCanvas.delete(self.zeigerKreis)
        windowCanvas.delete(self.derStrichSchatten)
        windowCanvas.delete(self.derStrich)

    def updateAnzeige(self):

        windowCanvas.delete(self.zeigerKreisSchatten)
        windowCanvas.delete(self.zeigerKreis)
        windowCanvas.delete(self.derStrichSchatten)
        windowCanvas.delete(self.derStrich)

        self.EinLabelWert.config(text = str(int(self.meinMessobjekt.value)) + " " + self.einheit)
        self.EinLabelWert2.config(text = self.name)

        self.zeichneBewegicheTeile()

    def zeichneBewegicheTeile(self):

        self.winkelHilfe = float(int(self.meinMessobjekt.value) / self.meinMessobjekt.MaximalerMesswert * math.pi*1.6 + math.pi*0.2)

        self.derStrichSchatten = windowCanvas.create_line(
            self.mittelpunktX + self.schattenXoffset,
            self.mittelpunktY + self.schattenYoffset,
            self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.zeigerLaenge - 2) + self.schattenXoffset,
            self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.zeigerLaenge - 2) + self.schattenXoffset,
            fill = self.farbeRundinstrumentSchatten,
            width = self.zeigerBreite
        )

        self.zeigerKreisSchatten = windowCanvas.create_oval(
            self.mittelpunktX - self.zeigerKreisRadius + self.schattenXoffset,
            self.mittelpunktY - self.zeigerKreisRadius + self.schattenYoffset,
            self.mittelpunktX + self.zeigerKreisRadius + self.schattenXoffset,
            self.mittelpunktY + self.zeigerKreisRadius + self.schattenYoffset,
            outline = self.farbeRundinstrumentSchatten,
            fill = self.farbeRundinstrumentSchatten
        )

        self.derStrich = windowCanvas.create_line(
            self.mittelpunktX,
            self.mittelpunktY,
            self.mittelpunktX + math.cos(self.winkelHilfe + self.winkelKonstante) * (self.zeigerLaenge - 2),
            self.mittelpunktY + math.sin(self.winkelHilfe + self.winkelKonstante) * (self.zeigerLaenge - 2),
            fill = self.farbeRundinstrumentZeiger,
            width = self.zeigerBreite
        )

        self.zeigerKreis = windowCanvas.create_oval(
            self.mittelpunktX - self.zeigerKreisRadius,
            self.mittelpunktY - self.zeigerKreisRadius,
            self.mittelpunktX + self.zeigerKreisRadius,
            self.mittelpunktY + self.zeigerKreisRadius,
            fill = self.farbeRundinstrumentZeiger
        )



class Hilfslinien:

    # Konstruktor fuer ein Hilfslinien Objekt
    # Ein Hilfslinien Objekt besteht aus mehreren Hilfslinien fuer ein Graphen  Objekt
    def __init__(self, eingabeCanvas, eingabeAbstandZumRand, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeYachseMaxWert, eingabeYachseMinWert, eingabeHilfslinienDicke):

        self.farbeHilfslinie = None
        self.farbeHilfslinienLabelsBackground = None
        self.farbeHilfslinienLabelsForeground = None

        self.meinCanvas = eingabeCanvas
        self.abstandZumRand = eingabeAbstandZumRand

        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2

        self.Hilfslinienabstand = Aufrunden125(int((eingabeYachseMaxWert - eingabeYachseMinWert) / 10))
        self.yAchseMaxWert = eingabeYachseMaxWert
        self.yAchseMinWert = eingabeYachseMinWert
        self.hilfslinienDicke = eingabeHilfslinienDicke
        self.linien = np.array([])
        self.labels = np.array([])

    def setHilfslinienColorScheme(self, istTag):
        if istTag:
            self.farbeHilfslinie = "grey10"
            self.farbeHilfslinienLabelsBackground = "grey90"
            self.farbeHilfslinienLabelsForeground = "grey0"
        else:
            self.farbeHilfslinie = "grey99"
            self.farbeHilfslinienLabelsBackground = "grey10"
            self.farbeHilfslinienLabelsForeground = "grey99"

    def zeichnen(self):

        # Umrechnen des Abstands in Pixel
        self.HilfslinienabstandPixel= int(self.Hilfslinienabstand * (self.posY2-self.posY1)/(self.yAchseMaxWert-self.yAchseMinWert))

        # For Schleife die so oft wiederholt wird wie es Hilfslinien geben soll
        for i in range (0, int((self.yAchseMaxWert - self.yAchseMinWert) / self.Hilfslinienabstand + 0.9999)):

            # Auf der Achse selber soll es keine Hilfslinie geben, daher if Abfrage
            if i != 0:
                # Hinzufuegen der Hiflslinien zum Array
                self.linien = np.append (self.linien, [windowCanvas.create_line(
                    self.posX1,
                    self.posY2 - self.HilfslinienabstandPixel * i,
                    self.posX2,
                    self.posY2 - self.HilfslinienabstandPixel*i,
                    fill= self.farbeHilfslinie,
                    width= self.hilfslinienDicke,
                    dash=(1,5)
                )])

            # Hinzufuegen der Beschriftung der Labels fuer die Hilfslinien
            self.labels = np.append (self.labels, [Label(
                root,
                text = self.yAchseMinWert + self.Hilfslinienabstand * i,
                bg = self.farbeHilfslinienLabelsBackground,
                fg=self.farbeHilfslinienLabelsForeground,
                font=("fixedsys", 10)
            )])

            self.labels[i].pack()
            self.labels[i].place(
                x=self.posX1 - self.abstandZumRand * 0.5,
                y=self.posY2 - self.HilfslinienabstandPixel * i,
                anchor="e"
            )

    def update(self, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeYachseMaxWert, eingabeYachseMinWert):
        self.Hilfslinienabstand = Aufrunden125(int((eingabeYachseMaxWert - eingabeYachseMinWert) / 10))
        self.yAchseMaxWert = eingabeYachseMaxWert
        self.yAchseMinWert = eingabeYachseMinWert
        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2

    def delete(self):
        for Linie in np.nditer(self.linien):
            windowCanvas.delete(int(Linie))
        self.linien = np.array([])

        for i in range(0, self.labels.size):
            self.labels[i].destroy()
        self.labels = np.array([])


class WertegruppenElement:

    def __init__(self, eingabeRoot, eingabeWerteX, eingabeWerteY, eingabeMessobjekt):

        self.root = eingabeRoot
        self.meinMessobjekt = eingabeMessobjekt

        self.einheit = self.meinMessobjekt.MesswertEinheit
        self.name = self.meinMessobjekt.MesswertName

        self.wertePosX = eingabeWerteX
        self.wertePosY = eingabeWerteY

        self.farbeWertegruppeBackground = None
        self.farbeWertegruppeForeground = None
        self.setWertegruppenElementColorScheme(True)

    def setWertegruppenElementColorScheme(self, istTag):
        if istTag:
            self.farbeWertegruppeBackground = self.meinMessobjekt.istTagFarbe
        else:
            self.farbeWertegruppeBackground = self.meinMessobjekt.istNachtFarbe
        self.farbeWertegruppeForeground = Luminance(self.farbeWertegruppeBackground)

    def zeichnen(self):
        self.einLabelWert = Label(
            self.root,
            text="0",
            bg=self.farbeWertegruppeBackground,
            fg=self.farbeWertegruppeForeground,
            font=("fixedsys", 12)
        )
        self.einLabelWert.pack()
        self.einLabelWert.place(x = self.wertePosX, y = self.wertePosY, anchor = "w")

    def delete(self):
        self.einLabelWert.destroy()

    def update(self, eingabeWerteX, eingabeWerteY):
        self.wertePosX = eingabeWerteX
        self.wertePosY = eingabeWerteY

    # Aktualisiert nur die Anzeige, fordert das Messobjekt aber NICHT dazu auf, dessen Wert vom Datastream zu refreshen
    def updateAnzeige(self):
        #        self.EinLabelWert.config(text = str(int(WertegruppeWert)) + " " + WertegruppeEinheit + " (" + WertegruppeName + ")")
        self.einLabelWert.config(text = str((self.meinMessobjekt.value)) + " " + self.einheit + " (" + self.name + ")")


class Wertegruppe:

    def __init__(self, eingabeRoot, eingabePosX1, eingabePosY1, eingabeMessobjekteArray):

        self.root = eingabeRoot
        self.posX1 = eingabePosX1
        self.posY1 = eingabePosY1
        self.WertegruppenElemente = np.array([])

        labelCounter = 0 # wichtig fuer Abstand zwischen den Labels
        for einMessobjekt in eingabeMessobjekteArray:
            self.WertegruppenElemente = np.append(self.WertegruppenElemente, WertegruppenElement(self.root, self.posX1, self.posY1 + labelCounter*25, einMessobjekt))
            labelCounter = labelCounter + 1

    def setWertegruppeColorScheme(self, istTag):
        for einElement in self.WertegruppenElemente:
            einElement.setWertegruppenElementColorScheme(istTag)

    def zeichnen(self):
        for einElement in self.WertegruppenElemente:
            einElement.zeichnen()

    def update(self, eingabePosX1, eingabePosY1):
        self.posX1 = eingabePosX1
        self.posY1 = eingabePosY1

        labelCounter = 0 # wichtig fuer Abstand zwischen den Labels
        for einElement in self.WertegruppenElemente:
            einElement.update(self.posX1, self.posY1 + labelCounter*25)
            labelCounter = labelCounter + 1

    def delete(self):
        for einElement in self.WertegruppenElemente:
            einElement.delete()

    def updateAnzeige(self):
        for einElement in self.WertegruppenElemente:
            einElement.updateAnzeige()


class GraphenLinie:

    def __init__(self, eingabeCanvas, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeMessobjekt, eingabeHistoryGröße):
        self.meinCanvas = eingabeCanvas

        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2

        self.meinMessobjekt = eingabeMessobjekt
        self.historyGröße = eingabeHistoryGröße

        self.farbeGraphenLinie = None
        self.setColorScheme(True)

        self.data = np.array([])
        self.linien = np.array([])

    def updateAnzeige(self):
        while self.data.size * grXsampling >= abs(self.posX2-self.posX1):
            self.data = np.delete(self.data, 0, axis=0)
        self.data = np.append(self.data, self.meinMessobjekt.value)

        for eineLinie in self.linien:
            self.meinCanvas.delete(int(eineLinie))
        self.linien = np.array([])

        for i in range(0, self.data.size-1):
            y1 = self.posY2 - max(0, min((self.data.item(i) - self.meinMessobjekt.MinimalerYachsenWert) / (self.meinMessobjekt.MaximalerYachsenWert - self.meinMessobjekt.MinimalerYachsenWert) * (self.posY2-self.posY1), (self.posY2-self.posY1)))
            y2 = self.posY2 - max(0, min((self.data.item(i+1) - self.meinMessobjekt.MinimalerYachsenWert) / (self.meinMessobjekt.MaximalerYachsenWert - self.meinMessobjekt.MinimalerYachsenWert) * (self.posY2-self.posY1), (self.posY2-self.posY1)))
            x1 = int(self.posX2 - (i  ) * grXsampling)
            x2 = int(self.posX2 - (i+1) * grXsampling)

            self.linien = np.append(self.linien, [self.meinCanvas.create_line(x1, y1, x2, y2, fill = self.farbeGraphenLinie, width= 1)])

    def update(self, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2):
        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2

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
        self.achsenBeschriftung = Label(self.meinCanvas, text = self.achsenBeschriftungText, bg = self.achsenBeschriftungFarbeBackground, fg = self.achsenBeschriftungFarbe, font=("fixedsys", 20))
        self.achsenBeschriftung.place(x = self.xAchseAnfang, y=self.yAchseEnde, anchor="n")

    # Update Funktion setzt nur die Werte neu und macht NIX grafisches!
    def update(self, eingabeXachseAnfang,eingabeXachseEnde,eingabeYachseAnfang,eingabeYachseEnde):
        self.xAchseAnfang = eingabeXachseAnfang
        self.xAchseEnde = eingabeXachseEnde
        self.yAchseAnfang = eingabeYachseAnfang
        self.yAchseEnde = eingabeYachseEnde

    # Delete Funktion löscht nur die Linien, nicht das Objekt an sich!
    def delete(self):
        if(self.dieXAchse != None and self.dieYAchse != None):
            self.meinCanvas.delete(self.dieXAchse)
            self.meinCanvas.delete(self.dieYAchse)
        self.achsenBeschriftung.destroy()

class Graph:

    def __init__(self, eingabeCanvas, eingabeAbstandZumRand, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeGraphenLegendenHoehe, eingabeMessobjekte):
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
        self.yAchsenMinUndMaxBestimmen()

        self.koordinatenSystem = KoordinatenSystem(self.meinCanvas, self.abstandZumRand, 2, self.posX1, self.posX2, self.posY2, self.posY1+self.graphenLegendenHoehe, self.Messobjekte[0].MesswertEinheit)
        self.hilfslinien = Hilfslinien(self.meinCanvas, self.abstandZumRand, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, self.MaximalerYachsenWert, self.MinimalerYachsenWert, "1")

        self.linien = np.array([])

        for einMessobjekt in eingabeMessobjekte:
            self.linien = np.append(self.linien, GraphenLinie(self.meinCanvas, self.posX1, self.posX2, self.posY1, self.posY2, einMessobjekt, 10))

    def yAchsenMinUndMaxBestimmen(self):
        for einMessobjekt in self.Messobjekte:
            if einMessobjekt.MaximalerYachsenWert > self.MaximalerYachsenWert:
                self.MaximalerYachsenWert = einMessobjekt.MaximalerYachsenWert
            if einMessobjekt.MinimalerYachsenWert < self.MinimalerYachsenWert:
                self.MinimalerYachsenWert = einMessobjekt.MinimalerYachsenWert

    def setGraphColorScheme(self, istTag):
        self.hilfslinien.setHilfslinienColorScheme(istTag)

    # macht nur die Werte neu, ist NICHT fuers neu zeichnen zustaendig
    def update(self, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2):

        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2

        self.hilfslinien.update(self.posX1, self.posX2, self.posY1, self.posY2, self.MaximalerYachsenWert, self.MinimalerYachsenWert)
        self.koordinatenSystem.update(self.posX1, self.posX2, self.posY2, self.posY1+self.graphenLegendenHoehe)

        for eineGraphenLinie in self.linien:
            eineGraphenLinie.update(self.posX1, self.posX2, self.posY1, self.posY2)

    def updateAnzeige(self):

        for eineGraphenLinie in self.linien:
            eineGraphenLinie.updateAnzeige()

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

        # Farben
        self.farbeDockBackground = None
        self.farbeDockLabelBackground = None
        self.farbeDockLabelForeground = None
        self.farbeDockTaste = None
        self.farbeDockEingabeBackground = None
        self.farbeDockEingabeForeground = None
        self.setColorScheme(True)

        self.dockFont = "fixedsys"
        self.dockFontSize = int(self.dockHoehe/3*fontsizefaktor)

        self.dockFrame = Frame(self.root)
        self.dockFrame.pack()

        self.dockValues = None
        self.schiebeRegler = None
        self.tastenLabels = None

        self.buttons = np.array([
            Button(self.dockFrame, text="QUIT", fg="red", command=self.root.destroy),
            Button(self.dockFrame, text="Kal", command=self.dockFrame.quit),
            Button(self.dockFrame, text="Restart", command=self.dockFrame.quit),
            Button(self.dockFrame, text="Shutdown", command=self.dockFrame.quit),
            Button(self.dockFrame, text="Benutzer", command=self.dockFrame.quit),
            Button(self.dockFrame, text="Design", command=self.zugriffAufApp.toggleColorScheme)
        ])

        for einButton in self.buttons:
            einButton.pack(side=LEFT)

    def setColorScheme(self, istTag):
        if istTag:
            self.farbeDockBackground = "grey60"
            self.farbeDockLabelBackground = "grey60"
            self.farbeDockLabelForeground = "grey30"
            self.farbeDockTaste = "blue"
            self.farbeDockEingabeBackground = "grey60"
            self.farbeDockEingabeForeground = "grey30"
        else:
            self.farbeDockBackground = "grey30"
            self.farbeDockLabelBackground = "grey30"
            self.farbeDockLabelForeground = "grey60"
            self.farbeDockTaste = "skyblue"
            self.farbeDockEingabeBackground = "grey30"
            self.farbeDockEingabeForeground = "grey60"

    def zeichnen(self):

        self.dockRechteck = self.meinCanvas.create_rectangle(self.dockX1,self.dockY1, self.dockX2, self.dockY2, fill = self.farbeDockBackground)

        self.dockValues = {
            "Sampling" : Label(
                self.root,
                text="Sampling",
                bg=self.farbeDockLabelBackground,
                fg=self.farbeDockLabelForeground,
                font=(self.dockFont, self.dockFontSize)
            ),
            "Start" : Label(
                self.root,
                text="Start",
                bg=self.farbeDockLabelBackground,
                fg=self.farbeDockLabelForeground,
                font=(self.dockFont, self.dockFontSize)
            ),
            "Label3" : Label(
                self.root, text="Hallo1",
                bg=self.farbeDockLabelBackground,
                fg=self.farbeDockLabelForeground,
                font=(self.dockFont, self.dockFontSize)
            ),
            "Label4" : Label(
                self.root, text="Hallo2",
                bg=self.farbeDockLabelBackground,
                fg="red",
                font=(self.dockFont, self.dockFontSize)
            ),
            "Label5" : Label(
                self.root, text="Hallo3",
                bg=self.farbeDockLabelBackground,
                fg="red",
                font=(self.dockFont, self.dockFontSize)
            ),
        }

        for key in self.dockValues:
            self.dockValues[key].pack()

        self.dockValues["Sampling"].place(  x = self.dockX1 + self.abstandZumRand + self.dockFontSize*11.5, y = self.dockY1 + self.dockHoehe * 0.5, anchor = "e")
        self.dockValues["Start"].place(     x = self.dockX2 - self.abstandZumRand,                          y = self.dockY1 + self.dockHoehe * 0.5, anchor = "e")
        self.dockValues["Label3"].place(    x = self.dockX2 - self.abstandZumRand - 300,                    y = self.dockY1 + self.dockHoehe * 0.5, anchor = "e")
        self.dockValues["Label4"].place(    x = self.dockX2 - self.abstandZumRand - 500,                    y = self.dockY1 + self.dockHoehe * 0.5, anchor = "e")
        self.dockValues["Label5"].place(    x = self.dockX2 - self.abstandZumRand - 700,                    y = self.dockY1 + self.dockHoehe * 0.5, anchor = "e")



        self.schiebeRegler = {
            "Horizontale Teilung" : Scale(
                self.root,
                from_ = 10,
                to = 90,
                length = 400,
                orient = HORIZONTAL,
                label = "Horizontale Teilung",
                bg = self.farbeDockEingabeBackground,
                fg = self.farbeDockEingabeForeground
            ),
            "Vertikale Teilung" : Scale(
                self.root,
                from_ = 30,
                to = 70,
                length = 50,
                orient = VERTICAL,
                label = "Vertikale Teilung",
                bg = self.farbeDockEingabeBackground,
                fg = self.farbeDockEingabeForeground
            ),
            "Glättung" : Scale(
                self.root,
                from_ = 0,
                to = 20,
                length = 50,
                orient = VERTICAL,
                label = "Glättung",
                bg = self.farbeDockEingabeBackground,
                fg = self.farbeDockEingabeForeground
            )
        }

        self.schiebeRegler["Horizontale Teilung"].set(self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterBreiteAufteilungWertegruppenRundinstrumente"])
        self.schiebeRegler["Horizontale Teilung"].place(
            x = self.dockX1 + self.abstandZumRand + self.dockFontSize * 11.5 + self.abstandZumRand * 4,
            y = self.dockY1 + self.abstandZumRand,
            width = 200,
            height = self.dockHoehe - self.abstandZumRand * 2
        )

        self.schiebeRegler["Vertikale Teilung"].set(self.zugriffAufApp.meinConfigHandler.appBestimmendeMasse["fensterHoeheAufteilungWertegruppenRundinstrumente"])
        self.schiebeRegler["Vertikale Teilung"].place(
            x = self.dockX1 + self.abstandZumRand + self.dockFontSize * 11.5 + self.abstandZumRand * 4 + 200 + self.abstandZumRand * 4,
            y = self.dockY1 + self.abstandZumRand,
            width = 160,
            height = self.dockHoehe - self.abstandZumRand * 2
        )

        self.schiebeRegler["Glättung"].set(self.zugriffAufApp.Glättung)
        self.schiebeRegler["Glättung"].place(
            x = self.dockX1 + self.abstandZumRand + self.dockFontSize * 11.5 + self.abstandZumRand * 4 + 200 + self.abstandZumRand * 4 + 160 + self.abstandZumRand * 4,
            y = self.dockY1 + self.abstandZumRand,
            width = 120,
            height = self.dockHoehe - self.abstandZumRand * 2
        )

        self.tastenLabels = {
            "1": Label(
                self.root,
                text = " 1 ",
                bg = self.farbeDockTaste,
                fg = self.farbeDockLabelBackground,
                font = (self.dockFont, int(self.dockFontSize))
            ),
            "2": Label(
                self.root,
                text = " 2 ",
                bg = self.farbeDockTaste,
                fg = self.farbeDockLabelBackground,
                font = (self.dockFont, int(self.dockFontSize))
            ),
            "3": Label(
                self.root,
                text = " 3 ",
                bg = self.farbeDockTaste,
                fg = self.farbeDockLabelBackground,
                font = (self.dockFont, int(self.dockFontSize))
            ),
            "4": Label(
                self.root,
                text = " 4 ",
                bg = self.farbeDockTaste,
                fg = self.farbeDockLabelBackground,
                font = (self.dockFont, int(self.dockFontSize))
            ),
            "Kalibrieren": Label(
                self.root,
                text = "Kalibr.",
                bg = self.farbeDockLabelBackground,
                fg = self.farbeDockTaste,
                font = (self.dockFont, int(self.dockFontSize*0.75))
            ),
            "EH Schub": Label(
                self.root,
                text = "EH_Sch.",
                bg = self.farbeDockLabelBackground,
                fg = self.farbeDockTaste,
                font = (self.dockFont, int(self.dockFontSize*0.75))
            ),
            "Glätten": Label(
                self.root,
                text = " Glätt.",
                bg = self.farbeDockLabelBackground,
                fg = self.farbeDockTaste,
                font = (self.dockFont, int(self.dockFontSize*0.75))
            ),
            "T/N": Label(
                self.root,
                text = " T/N",
                bg = self.farbeDockLabelBackground,
                fg = self.farbeDockTaste,
                font = (self.dockFont, int(self.dockFontSize*0.75))
            )
        }

        for key in self.tastenLabels:
            self.tastenLabels[key].pack()

        self.tastenLabels["1"].place(
            x = (self.dockX2-self.dockX1)/2-90,
            y = self.dockY1+self.dockHoehe*0.3,
            anchor="c"
        )
        self.tastenLabels["2"].place(
            x = (self.dockX2-self.dockX1)/2-30,
            y = self.dockY1+self.dockHoehe*0.3,
            anchor="c"
        )
        self.tastenLabels["3"].place(
            x = (self.dockX2-self.dockX1)/2+30,
            y = self.dockY1+self.dockHoehe*0.3,
            anchor="c"
        )
        self.tastenLabels["4"].place(
            x = (self.dockX2-self.dockX1)/2+90,
            y = self.dockY1+self.dockHoehe*0.3,
            anchor="c"
        )
        self.tastenLabels["Kalibrieren"].place(
            x = (self.dockX2-self.dockX1)/2-90,
            y = self.dockY1+self.dockHoehe*0.7,
            anchor="c"
        )
        self.tastenLabels["EH Schub"].place(
            x = (self.dockX2-self.dockX1)/2-30,
            y = self.dockY1+self.dockHoehe*0.7,
            anchor="c"
        )
        self.tastenLabels["Glätten"].place(
            x = (self.dockX2-self.dockX1)/2+30,
            y = self.dockY1+self.dockHoehe*0.7,
            anchor="c"
        )
        self.tastenLabels["T/N"].place(
            x = (self.dockX2-self.dockX1)/2+90,
            y = self.dockY1+self.dockHoehe*0.7,
            anchor="c"
        )

    def delete(self):
        self.meinCanvas.delete(self.dockRechteck)
        for key in self.dockValues:
            self.dockValues[key].destroy()
        for key in self.schiebeRegler:
            self.schiebeRegler[key].destroy()
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


class RundinstrumentenGruppe:

    def __init__ (self, eingabeRoot, eingabeMessobjekte, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeSchattenXoffset, eingabeSchattenYoffset):

        self.root = eingabeRoot
        self.meineMessobjekte = None
        if eingabeMessobjekte.size > 6:
            self.meineMessobjekte = eingabeMessobjekte[0:6]
            print("Zu viele Rundinstrumente in dieser Gruppe!")
        else:
            self.meineMessobjekte = eingabeMessobjekte

        self.einzelneRundinstrumentPositionen = np.array([])
        self.allgemeinerRadius = None

        self.update(eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2)

        self.meineRundinstrumente = np.array([])

        for einMessobjekt, einePosition  in zip(self.meineMessobjekte, self.einzelneRundinstrumentPositionen):
            self.meineRundinstrumente = np.append(self.meineRundinstrumente, [Rundinstument(
                self.root,
                einMessobjekt,
                einePosition[0],
                einePosition[1],
                einePosition[2],
                einePosition[3],
                self.allgemeinerRadius,
                eingabeSchattenXoffset,
                eingabeSchattenYoffset)
            ])

    def update(eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2):
        self.posX1 = eingabePosX1
        self.posX2 = eingabePosX2
        self.posY1 = eingabePosY1
        self.posY2 = eingabePosY2

        # Array mit einzelnen Positionen der Rundinstrumente
        self.einzelneRundinstrumentPositionen = np.array([])

        if self.meineMessobjekte.size < 5:
            if self.meineMessobjekte.size == 1:
                # Ein Rundinstrument, Radius ist die kleiner der beiden Seitenlängen
                self.allgemeinerRadius = min(self.posX2-self.posX1, self.posY2-self.posY1)
                self.einzelneRundinstrumentPositionen = np.array([np.array([
                    self.posX1 + (self.posX2-self.posX1)/2 - self.allgemeinerRadius,
                    self.posX1 + (self.posX2-self.posX1)/2 + self.allgemeinerRadius,
                    self.posY1 + (self.posY2-self.posY1)/2 - self.allgemeinerRadius,
                    self.posY1 + (self.posY2-self.posY1)/2 + self.allgemeinerRadius
                ])])

            elif self.meineMessobjekte.size == 2:
                # Zwei Rundinstrumente
                if (self.posX2-self.posX1) >= (self.posY2-self.posY1)*2:
                    # Die Rundinstrumente sollen nebeneinander sein -> Radius = Höhe
                    self.allgemeinerRadius == self.posY2-self.posY1
                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + (self.posX2 - self.posX1)/3 - self.allgemeinerRadius,
                            self.posX1 + (self.posX2 - self.posX1)/3 + self.allgemeinerRadius,
                            self.posY1 + (self.posY2 - self.posY1)/2 - self.allgemeinerRadius,
                            self.posY1 + (self.posY2 - self.posY1)/2 + self.allgemeinerRadius
                        ]),
                        np.array([
                            self.posX1 + 2*(self.posX2 - self.posX1)/3 - self.allgemeinerRadius,
                            self.posX1 + 2*(self.posX2 - self.posX1)/3 + self.allgemeinerRadius,
                            self.posY1 + (self.posY2 - self.posY1)/2 - self.allgemeinerRadius,
                            self.posY1 + (self.posY2 - self.posY1)/2 + self.allgemeinerRadius
                        ])
                    ])

                else:
                    # Die Rundinstrumente sollen übereinander sein -> Radius = Breite
                    self.allgemeinerRadius == self.posX2-self.posX1
                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + (self.posX2 - self.posX1)/2 - self.allgemeinerRadius,
                            self.posX1 + (self.posX2 - self.posX1)/2 + self.allgemeinerRadius,
                            self.posY1 + (self.posY2 - self.posY1)/3 - self.allgemeinerRadius,
                            self.posY1 + (self.posY2 - self.posY1)/3 + self.allgemeinerRadius
                        ]),
                        np.array([
                            self.posX1 + (self.posX2 - self.posX1)/2 - self.allgemeinerRadius,
                            self.posX1 + (self.posX2 - self.posX1)/2 + self.allgemeinerRadius,
                            self.posY1 + 2*(self.posY2 - self.posY1)/3 - self.allgemeinerRadius,
                            self.posY1 + 2*(self.posY2 - self.posY1)/3 + self.allgemeinerRadius
                        ])
                    ])

            elif self.meineMessobjekte.size == 3:
                # Drei Rundinstumente
                if (self.posX2-self.posX1) >= (self.posY2-self.posY1)*3:
                    # Die Rundinstrumente sollen nebeneinander sein -> Radius = Höhe
                    self.allgemeinerRadius == self.posY2-self.posY1

                    oberePosY = self.posY1 + (self.posY2 - self.posY1)/2 - self.allgemeinerRadius
                    unterePosY = self.posY1 + (self.posY2 - self.posY1)/2 + self.allgemeinerRadius

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + (self.posX2 - self.posX1)/4 - self.allgemeinerRadius,
                            self.posX1 + (self.posX2 - self.posX1)/4 + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + (self.posX2 - self.posX1)/2 - self.allgemeinerRadius,
                            self.posX1 + (self.posX2 - self.posX1)/2 + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + 3*(self.posX2 - self.posX1)/4 - self.allgemeinerRadius,
                            self.posX1 + 3*(self.posX2 - self.posX1)/4 + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ])
                    ])
                else:
                    # Die Rundinstrumente sollen übereinander sein -> Radius = Breite
                    self.allgemeinerRadius == self.posX2-self.posX1

                    linkePosX = self.posX1 + (self.posX2 - self.posX1)/2 - self.allgemeinerRadius
                    RechtePosX = self.posX1 + (self.posX2 - self.posX1)/2 + self.allgemeinerRadius

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + (self.posY2 - self.posY1)/4 - self.allgemeinerRadius,
                            self.posY1 + (self.posY2 - self.posY1)/4 + self.allgemeinerRadius
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + (self.posY2 - self.posY1)/2 - self.allgemeinerRadius,
                            self.posY1 + (self.posY2 - self.posY1)/2 + self.allgemeinerRadius
                        ]),
                        np.array([
                            linkePosX,
                            RechtePosX,
                            self.posY1 + 3*(self.posY2 - self.posY1)/4 - self.allgemeinerRadius,
                            self.posY1 + 3*(self.posY2 - self.posY1)/4 + self.allgemeinerRadius
                        ])
                    ])

            elif self.meineMessobjekte.size == 4:
                # Vier Rundinstumente
                if (self.posX2-self.posX1) >= (self.posY2-self.posY1)*4:
                    # Die Rundinstrumente sollen nebeneinander sein -> Radius = Höhe
                    self.allgemeinerRadius == self.posY2-self.posY1

                    oberePosY = self.posY1 + (self.posY2 - self.posY1)/2 - self.allgemeinerRadius
                    unterePosY = self.posY1 + (self.posY2 - self.posY1)/2 + self.allgemeinerRadius

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + (self.posX2 - self.posX1)/5 - self.allgemeinerRadius,
                            self.posX1 + (self.posX2 - self.posX1)/5 + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + 2*(self.posX2 - self.posX1)/5 - self.allgemeinerRadius,
                            self.posX1 + 2*(self.posX2 - self.posX1)/5 + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + 3*(self.posX2 - self.posX1)/5 - self.allgemeinerRadius,
                            self.posX1 + 3*(self.posX2 - self.posX1)/5 + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + 4*(self.posX2 - self.posX1)/5 - self.allgemeinerRadius,
                            self.posX1 + 4*(self.posX2 - self.posX1)/5 + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ])
                    ])

                else:
                    if (self.posY2-self.posY1) > (self.posX2-self.posX1)*4:
                        # Die Rundinstrumente sollen übereinander sein -> Radius = Breite
                        self.allgemeinerRadius == self.posX2-self.posX1

                        # Auslagerung der Berechnungen damit nicht mehrmals durchgeführt werden müssen
                        linkePosX = self.posX1 + (self.posX2 - self.posX1)/2 - self.allgemeinerRadius
                        RechtePosX = self.posX1 + (self.posX2 - self.posX1)/2 + self.allgemeinerRadius

                        self.einzelneRundinstrumentPositionen = np.array([
                            np.array([
                                linkePosX,
                                RechtePosX,
                                self.posY1 + (self.posY2 - self.posY1)/5 - self.allgemeinerRadius,
                                self.posY1 + (self.posY2 - self.posY1)/5 + self.allgemeinerRadius
                            ]),
                            np.array([
                                linkePosX,
                                RechtePosX,
                                self.posY1 + 2*(self.posY2 - self.posY1)/5 - self.allgemeinerRadius,
                                self.posY1 + 2*(self.posY2 - self.posY1)/5 + self.allgemeinerRadius
                            ]),
                            np.array([
                                linkePosX,
                                RechtePosX,
                                self.posY1 + 3*(self.posY2 - self.posY1)/5 - self.allgemeinerRadius,
                                self.posY1 + 3*(self.posY2 - self.posY1)/5 + self.allgemeinerRadius
                            ]),
                            np.array([
                                linkePosX,
                                RechtePosX,
                                self.posY1 + 4*(self.posY2 - self.posY1)/5 - self.allgemeinerRadius,
                                self.posY1 + 4*(self.posY2 - self.posY1)/5 + self.allgemeinerRadius
                            ])
                        ])
                    else:
                        # Rundinstrumente in Quadrat anordnen
                        self.allgemeinerRadius = min((self.posX2-self.posX1)/2, (self.posY2-self.posY1)/2)

                        drittelAbstandX = (self.posX2 - self.posX1)/3
                        drittelAbstandY = (self.posY2 - self.posY1)/3

                        self.einzelneRundinstrumentPositionen = np.array([
                            np.array([
                                self.posX1 + drittelAbstandX - self.allgemeinerRadius,
                                self.posX1 + drittelAbstandX + self.allgemeinerRadius,
                                self.posY1 + drittelAbstandY - self.allgemeinerRadius,
                                self.posY1 + drittelAbstandY + self.allgemeinerRadius
                            ]),
                            np.array([
                                self.posX1 + 2*drittelAbstandX - self.allgemeinerRadius,
                                self.posX1 + 2*drittelAbstandX + self.allgemeinerRadius,
                                self.posY1 + drittelAbstandY - self.allgemeinerRadius,
                                self.posY1 + drittelAbstandY + self.allgemeinerRadius
                            ]),
                            np.array([
                                self.posX1 + drittelAbstandX - self.allgemeinerRadius,
                                self.posX1 + drittelAbstandX + self.allgemeinerRadius,
                                self.posY1 + 2*drittelAbstandY - self.allgemeinerRadius,
                                self.posY1 + 2*drittelAbstandY + self.allgemeinerRadius
                            ]),
                            np.array([
                                self.posX1 + 2*drittelAbstandX - self.allgemeinerRadius,
                                self.posX1 + 2*drittelAbstandX + self.allgemeinerRadius,
                                self.posY1 + 2*drittelAbstandY - self.allgemeinerRadius,
                                self.posY1 + 2*drittelAbstandY + self.allgemeinerRadius
                            ])
                        ])

        else:
            return # Rest muss noch implementiert werden
            if self.meineRundinstrumente.size == 5:
                # Fünf Rundinstumente
                if (self.posX2-self.posX1) >= (self.posY2-self.posY1)*5:
                    # Die Rundinstrumente sollen nebeneinander sein -> Radius = Höhe
                    self.allgemeinerRadius == self.posY2-self.posY1

                    oberePosY = self.posY1 + (self.posY2 - self.posY1)/2 - self.allgemeinerRadius
                    unterePosY = self.posY1 + (self.posY2 - self.posY1)/2 + self.allgemeinerRadius

                    sechstelXdifferenz = (self.posX2 - self.posX1)/6

                    self.einzelneRundinstrumentPositionen = np.array([
                        np.array([
                            self.posX1 + sechstelXdifferenz - self.allgemeinerRadius,
                            self.posX1 + sechstelXdifferenz + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + 2*sechstelXdifferenz - self.allgemeinerRadius,
                            self.posX1 + 2*sechstelXdifferenz + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + 3*sechstelXdifferenz - self.allgemeinerRadius,
                            self.posX1 + 3*sechstelXdifferenz + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + 4*sechstelXdifferenz - self.allgemeinerRadius,
                            self.posX1 + 4*sechstelXdifferenz + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ]),
                        np.array([
                            self.posX1 + 5*sechstelXdifferenz - self.allgemeinerRadius,
                            self.posX1 + 5*sechstelXdifferenz + self.allgemeinerRadius,
                            oberePosY,
                            unterePosY
                        ])
                    ])

                else:
                    if (self.posY2-self.posY1) > (self.posX2-self.posX1)*5:
                        # Die Rundinstrumente sollen übereinander sein -> Radius = Breite
                        self.allgemeinerRadius == self.posX2-self.posX1

                        # Auslagerung der Berechnungen damit nicht mehrmals durchgeführt werden müssen
                        linkePosX = self.posX1 + (self.posX2 - self.posX1)/2 - self.allgemeinerRadius
                        RechtePosX = self.posX1 + (self.posX2 - self.posX1)/2 + self.allgemeinerRadius

                        sechstelYdifferenz = (self.posY2 - self.posY1)/6

                        self.einzelneRundinstrumentPositionen = np.array([
                            np.array([
                                linkePosX,
                                RechtePosX,
                                self.posY1 + sechstelYdifferenz - self.allgemeinerRadius,
                                self.posY1 + sechstelYdifferenz + self.allgemeinerRadius
                            ]),
                            np.array([
                                linkePosX,
                                RechtePosX,
                                self.posY1 + 2*sechstelYdifferenz - self.allgemeinerRadius,
                                self.posY1 + 2*sechstelYdifferenz + self.allgemeinerRadius
                            ]),
                            np.array([
                                linkePosX,
                                RechtePosX,
                                self.posY1 + 3*sechstelYdifferenz - self.allgemeinerRadius,
                                self.posY1 + 3*sechstelYdifferenz + self.allgemeinerRadius
                            ]),
                            np.array([
                                linkePosX,
                                RechtePosX,
                                self.posY1 + 4*sechstelYdifferenz - self.allgemeinerRadius,
                                self.posY1 + 4*sechstelYdifferenz + self.allgemeinerRadius
                            ]),
                            np.array([
                                linkePosX,
                                RechtePosX,
                                self.posY1 + 5*sechstelYdifferenz - self.allgemeinerRadius,
                                self.posY1 + 5*sechstelYdifferenz + self.allgemeinerRadius
                            ])
                        ])

                    else:
                        if (self.posX2-self.posX1)*2 > (self.posY2-self.posY1)*3
                            # 2 Zeilen und Drei in einer Zeile
                            self.allgemeinerRadius = min((self.posX2-self.posX1)/3, (self.posY2-self.posY1)/2)

                            viertelAbstandX = (self.posX2 - self.posX1)/4 # Weil 3 "Spalten"
                            drittelAbstandY = (self.posY2 - self.posY1)/3 # Weil 2 "Zeilen"

                            self.einzelneRundinstrumentPositionen = np.array([
                                np.array([
                                    self.posX1 + viertelAbstandX - self.allgemeinerRadius,
                                    self.posX1 + viertelAbstandX + self.allgemeinerRadius,
                                    self.posY1 + drittelAbstandY - self.allgemeinerRadius,
                                    self.posY1 + drittelAbstandY + self.allgemeinerRadius
                                ]),
                                np.array([
                                    self.posX1 + 2*viertelAbstandX - self.allgemeinerRadius,
                                    self.posX1 + 2*viertelAbstandX + self.allgemeinerRadius,
                                    self.posY1 + drittelAbstandY - self.allgemeinerRadius,
                                    self.posY1 + drittelAbstandY + self.allgemeinerRadius
                                ]),
                                np.array([
                                    self.posX1 + 3*viertelAbstandX - self.allgemeinerRadius,
                                    self.posX1 + 3*viertelAbstandX + self.allgemeinerRadius,
                                    self.posY1 + drittelAbstandY - self.allgemeinerRadius,
                                    self.posY1 + drittelAbstandY + self.allgemeinerRadius
                                ]),
                                np.array([
                                    self.posX1 + viertelAbstandX - self.allgemeinerRadius,
                                    self.posX1 + viertelAbstandX + self.allgemeinerRadius,
                                    self.posY1 + 2*drittelAbstandY - self.allgemeinerRadius,
                                    self.posY1 + 2*drittelAbstandY + self.allgemeinerRadius
                                ]),
                                np.array([
                                    self.posX1 + 2*viertelAbstandX - self.allgemeinerRadius,
                                    self.posX1 + 2*viertelAbstandX + self.allgemeinerRadius,
                                    self.posY1 + 2*drittelAbstandY - self.allgemeinerRadius,
                                    self.posY1 + 2*drittelAbstandY + self.allgemeinerRadius
                                ])
                            ])

                        else:
                            # 3 Zeilen und Zwei in einer Zeile
                            self.allgemeinerRadius = min((self.posX2-self.posX1)/2, (self.posY2-self.posY1)/3)
                            drittelAbstandX = (self.posX2 - self.posX1)/3 # Weil 2 "Spalten"
                            viertelAbstandY = (self.posY2 - self.posY1)/4 # Weil 3 "Zeilen"

                            self.einzelneRundinstrumentPositionen = np.array([
                                np.array([
                                    self.posX1 + drittelAbstandX - self.allgemeinerRadius,
                                    self.posX1 + drittelAbstandX + self.allgemeinerRadius,
                                    self.posY1 + viertelAbstandY - self.allgemeinerRadius,
                                    self.posY1 + viertelAbstandY + self.allgemeinerRadius
                                ]),
                                np.array([
                                    self.posX1 + 2*drittelAbstandX - self.allgemeinerRadius,
                                    self.posX1 + 2*drittelAbstandX + self.allgemeinerRadius,
                                    self.posY1 + viertelAbstandY - self.allgemeinerRadius,
                                    self.posY1 + viertelAbstandY + self.allgemeinerRadius
                                ]),
                                np.array([
                                    self.posX1 + drittelAbstandX - self.allgemeinerRadius,
                                    self.posX1 + drittelAbstandX + self.allgemeinerRadius,
                                    self.posY1 + 2*viertelAbstandY - self.allgemeinerRadius,
                                    self.posY1 + 2*viertelAbstandY + self.allgemeinerRadius
                                ]),
                                np.array([
                                    self.posX1 + 2*drittelAbstandX - self.allgemeinerRadius,
                                    self.posX1 + 2*drittelAbstandX + self.allgemeinerRadius,
                                    self.posY1 + 2*viertelAbstandY - self.allgemeinerRadius,
                                    self.posY1 + 2*viertelAbstandY + self.allgemeinerRadius
                                ]),
                                np.array([
                                    self.posX1 + drittelAbstandX - self.allgemeinerRadius,
                                    self.posX1 + drittelAbstandX + self.allgemeinerRadius,
                                    self.posY1 + 3*viertelAbstandY - self.allgemeinerRadius,
                                    self.posY1 + 3*viertelAbstandY + self.allgemeinerRadius
                                ])
                            ])


            elif self.meineRundinstrumente.size == 6:
                # Sechs Rundinstumente
                if (self.posX2-self.posX1) >= (self.posY2-self.posY1)*6:
                    # Die Rundinstrumente sollen nebeneinander sein -> Radius = Höhe
                    self.allgemeinerRadius == self.posY2-self.posY1

                else:
                    if (self.posY2-self.posY1) > (self.posX2-self.posX1)*6:
                        # Die Rundinstrumente sollen übereinander sein -> Radius = Breite
                        self.allgemeinerRadius == self.posX2-self.posX1
                    else:
                        if (self.posX2-self.posX1)*2 > (self.posY2-self.posY1)*3
                            # 2 Zeilen und Drei in einer Zeile
                            self.allgemeinerRadius = min((self.posX2-self.posX1)/3, (self.posY2-self.posY1)/2)
                        else:
                            # 3 Zeilen und Zwei in einer Zeile
                            self.allgemeinerRadius = min((self.posX2-self.posX1)/2, (self.posY2-self.posY1)/3)


            # elif self.meineRundinstrumente.size == 7:
            #     # Sieben Rundinstumente
            #     if (self.posX2-self.posX1) >= (self.posY2-self.posY1)*7:
            #         # Die Rundinstrumente sollen nebeneinander sein -> Radius = Höhe
            #         self.allgemeinerRadius == self.posY2-self.posY1
            #
            #     else:
            #         if (self.posY2-self.posY1) > (self.posX2-self.posX1)*7:
            #             # Die Rundinstrumente sollen übereinander sein -> Radius = Breite
            #             self.allgemeinerRadius == self.posX2-self.posX1
            #         else:
            #             if (self.posX2-self.posX1)*2 > (self.posY2-self.posY1)*4
            #                 # 2 Zeilen und Drei in einer Zeile
            #                 self.allgemeinerRadius = min((self.posX2-self.posX1)/3, (self.posY2-self.posY1)/2)
            #             else:
            #                 # 3 Zeilen und Zwei in einer Zeile
            #                 self.allgemeinerRadius = min((self.posX2-self.posX1)/2, (self.posY2-self.posY1)/3)
            #
            # elif self.meineRundinstrumente.size == 8:
            #     self.allgemeinerRadius = min((self.posX2-self.posX1)/2, (self.posY2-self.posY1)/2)
            else:
                print("Error bei Anordnen der Rundinstrumente")

        for einRundinstrument, einePosition in zip(self.meineRundinstrumente, self.einzelneRundinstrumentPositionen):
            einRundinstrument.update(einePosition[0], einePosition[1], einePosition[2], einePosition[3], self.allgemeinerRadius)

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


class App:
    def __init__(self, eingabeRoot, eingabeCanvas):

        # Farbvariablen
        self.Design = True
        self.farbeAppBackground = None
        self.farbeAppDock = None

        self.farbeWindowCanvasFrame = None

        self.farbeMesswertBackground = None
        self.farbeMesswertForeground = None

        self.farbeButtonForeground = None

        self.farbeAlarmBackground = None
        self.farbeAlarmForeground = None

        self.meinConfigHandler = configFileHandler("tp")
        self.meinConfigHandler.configLesen()
        self.meinConfigHandler.modocConfigLesen()
        self.meinUSBhandler = usbDataHandler()

        self.root = eingabeRoot
        self.meinCanvas = eingabeCanvas
        self.meinCanvas.config(width = self.meinConfigHandler.appBestimmendeMasse["fensterBreite"], height = self.meinConfigHandler.appBestimmendeMasse["fensterHoehe"])
        self.abstandZumRand = self.meinConfigHandler.appBestimmendeMasse["abstandZumRand"]
        self.dockHoehe = self.meinConfigHandler.appBestimmendeMasse["dockHoehe"]

        self.Glättung = 0

        self.MesswertObjekte = {
            "Drehzahl" :    Messobjekt("Drehzahl",      "U/m",  0, 20000,   0, 20000,   20,     10, 21, 0,  "#d50000", "#ef5350"),
            "Drehmoment" :  Messobjekt("Drehmoment",    "Ncm",  0, 400,     0, 400,     400,    10, 43, 1,  "#aa00ff", "#ec407a"),
            "Schub":        Messobjekt("Schub",         "kg",   0, 3000,    0, 3000,    3000,   6,  34, 2,  "#6200ea", "#9575cd"),
            "Leistung":     Messobjekt("Leistung",      "W",    0, 3000,    0, 3000,    3000,   7,  15, 3,  "#2962ff", "#42a5f5"),
            "Gas":          Messobjekt("Gas",           "%",    0, 100,     0, 100,     100,    16, 8,  4,  "#00b8d4", "#00b8d4"),
            "Temp1":        Messobjekt("Temp1",         "°C",   0, 400,     0, 300,     400,    16, 8,  9,  "#4caf50", "#4caf50"),
            "Temp2":        Messobjekt("Temp2",         "°C",   0, 400,     0, 300,     400,    16, 8,  10, "#00c853", "#00c853"),
            "Temp3":        Messobjekt("Temp3",         "°C",   0, 400,     0, 300,     400,    16, 8,  11, "#aeea00", "#aeea00"),
            "Temp4":        Messobjekt("Temp4",         "°C",   0, 400,     0, 300,     400,    16, 8,  12, "#827717", "#827717"),
            "Temp5":        Messobjekt("Temp5",         "°C",   0, 400,     0, 300,     400,    16, 8,  42, "#33691e", "#33691e"),
            "Temp6":        Messobjekt("Temp6",         "°C",   0, 400,     0, 300,     400,    16, 8,  43, "#8bc34a", "#8bc34a"),
            "Temp7":        Messobjekt("Temp7",         "°C",   0, 400,     0, 300,     400,    16, 8,  44, "#00796b", "#00796b"),
            "Temp8":        Messobjekt("Temp8",         "°C",   0, 400,     0, 300,     400,    16, 8,  45, "#004d40", "#004d40"),
            "VCC":          Messobjekt("VCC",           "V",    0, 20,      0, 20,      20,     16, 8,  27, "#ffab00", "#ffab00"),
            "TempCPU":      Messobjekt("TempCPU",       "°C",   0, 100,     0, 100,     100,    16, 8,  14, "#f44336", "#f44336"),
            "arduvers":     Messobjekt("arduvers",      "",     0, 0,       0, 0,       0,      0,  0,  41, "#000000", "#000000"),
            "shutdown":     Messobjekt("shutdown",      "",     0, 0,       0, 0,       0,      0,  0,  35, "#000000", "#000000"),
            "taste1":       Messobjekt("taste1",        "",     0, 0,       0, 0,       0,      0,  0,  36, "#000000", "#000000"),
            "taste2":       Messobjekt("taste2",        "",     0, 0,       0, 0,       0,      0,  0,  37, "#000000", "#000000"),
            "taste3":       Messobjekt("taste3",        "",     0, 0,       0, 0,       0,      0,  0,  38, "#000000", "#000000"),
            "taste4":       Messobjekt("taste4",        "",     0, 0,       0, 0,       0,      0,  0,  39, "#000000", "#000000"),

        }

        self.eineWertegruppe = Wertegruppe(self.root, 500, 100, [
            self.MesswertObjekte["Temp1"],
            self.MesswertObjekte["Temp2"],
            self.MesswertObjekte["Temp3"],
            self.MesswertObjekte["Temp4"],
            self.MesswertObjekte["Temp5"],
            self.MesswertObjekte["Temp6"],
            self.MesswertObjekte["Temp7"],
            self.MesswertObjekte["Temp8"],
        ])

        self.eineWertegruppe.zeichnen()

        #self, eingabeRoot, eingabeMessobjekt, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2, eingabeRadius, eingabeSchattenXoffset, eingabeSchattenYoffset
        self.Rundinstumente = RundinstrumentenGruppe(
            self.root,
            [self.MesswertObjekte["Drehzahl"], self.MesswertObjekte["Drehmoment"], self.MesswertObjekte["Leistung"]],
            750,
            1900,
            500,
            900,
            eingabePosX2,
            eingabePosY1,
            eingabePosY2,
            self.meinConfigHandler.appBestimmendeMasse["rundinstrumentSchattenXoffset"],
            self.meinConfigHandler.appBestimmendeMasse["rundinstrumentSchattenYoffset"]
        )

        self.Rundinstumente.zeichnen()

        self.Graphs = np.array([])
        self.Graphs = np.append(self.Graphs, [
            Graph(
                self.meinCanvas,
                self.abstandZumRand,
                self.abstandZumRand+50,
                self.meinCanvas.winfo_width()*0.5,
                0,
                500,
                50,
                np.array([
                    self.MesswertObjekte["Temp1"],
                    self.MesswertObjekte["Temp2"],
                    self.MesswertObjekte["Temp3"],
                    self.MesswertObjekte["Temp4"],
                    self.MesswertObjekte["Temp5"],
                    self.MesswertObjekte["Temp6"],
                    self.MesswertObjekte["Temp7"],
                    self.MesswertObjekte["Temp8"]
                ])
            )
        ])

        self.dock = Dock(self.root, self, self.meinCanvas, self.dockHoehe, self.abstandZumRand)
        self.dock.zeichnen()

        for einGraph in self.Graphs:
            einGraph.zeichnen()


    def resizeCallback(self, event):
        self.guiReset()

    def guiReset(self):
        self.eineWertegruppe.update(0.5*self.meinCanvas.winfo_width(),  0.1*self.meinCanvas.winfo_height())
        self.eineWertegruppe.delete()
        self.eineWertegruppe.zeichnen()
        self.eineWertegruppe.updateAnzeige()

        for einGraph in self.Graphs:
            einGraph.update(self.abstandZumRand+50, 0.5*self.meinCanvas.winfo_width(), self.abstandZumRand, self.meinCanvas.winfo_height() - self.dockHoehe - 20)
            einGraph.delete()
            einGraph.zeichnen()

        self.Rundinstumente.update(0.5*self.meinCanvas.winfo_width()+10, 0.5*self.meinCanvas.winfo_width()+300, 0.5*self.meinCanvas.winfo_height(), 0.5*self.meinCanvas.winfo_height()+300, 150)
        self.Rundinstumente.delete()
        self.Rundinstumente.zeichnen()

        self.dock.update(self.dockHoehe, self.abstandZumRand)
        self.dock.delete()
        self.dock.zeichnen()

        self.meinConfigHandler.appBestimmendeMasse["fensterBreite"] = self.meinCanvas.winfo_width()
        self.meinConfigHandler.appBestimmendeMasse["fensterHoehe"] = self.meinCanvas.winfo_height()
        self.meinConfigHandler.configSchreiben()


    def toggleColorScheme(self):
        self.Design = not self.Design
        for einGraph in self.Graphs:
            einGraph.setColorScheme(self.Design)
        self.Rundinstumente.setColorScheme(self.Design)
        self.dock.setColorScheme(self.Design)
        if self.Design:
            self.meinCanvas.config(bg = "white")
        else:
            self.meinCanvas.config(bg = "black")

        self.guiReset()


    def appLoop(self):

        lasttime = time.time()
        time.sleep(0.1)

        while True:

            # Berechnen und Anzeigen der Sampling Rate
            sampleRate = 1/(float(time.time() - lasttime))
            lasttime = time.time()
            self.dock.updateSamplingAnzeige(sampleRate)

            # Hier rufen alle Messwert Objekt ihren aktuellen Wert aus dem Data Stream ab
            self.meinUSBhandler.leseUSBline()
            for key in self.MesswertObjekte:
                self.MesswertObjekte[key].refreshYourValue(self.meinUSBhandler.data, self.meinConfigHandler.modocKonstanten)


            self.eineWertegruppe.updateAnzeige()

            self.Rundinstumente.updateAnzeige()

            self.Graphs[0].updateAnzeige()

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
        }

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

        self.username = eingabeUsername

        if istPruefstand:
            self.modocConfigfilename = "modoc_conf.csv"
        else:
            self.modocConfigfilename = "makerbeam_conf.csv"

        if rasp  == 1:
            self.configfilename = "/home/sp/config_" + self.username + ".csv"
            self.modocConfigfilename = "/home/sp/" + self.modocConfigfilename
        else:
            self.configfilename = "config_" + self.username + ".csv"

    def configLesen(self):
        ####################################################################################
        ### Lese Variable aus Configfile config_USER.csv / im Problemfall setze Defaultwerte
        ####################################################################################

        try:
            configfile = csv.reader(open(self.configfilename, "r"), delimiter=";")
        except FileNotFoundError:
            print ("Configfile: ", self.configfilename, " nicht gefunden!")

        configIdentifier = np.array([])
        configValue = np.array([])

        for spalte in configfile:
            configIdentifier = np.append(configIdentifier, spalte[0])
            configValue = np.append(configValue, spalte[1])

        AccessIndex = 0
        istFehlerfrei = True

        for identifier, value in self.appBestimmendeMasse.items():
            if(configIdentifier[AccessIndex] == identifier):
                self.appBestimmendeMasse[identifier] = int(configValue[AccessIndex])
            else:
                print("Falscher Inhalt in ", identifier, " : ", configIdentifier[AccessIndex])
                istFehlerfrei = False
            AccessIndex = AccessIndex + 1

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
            ["rundinstrumentSchattenYoffset", self.appBestimmendeMasse["rundinstrumentSchattenYoffset"]]
        )

        configfile.writerows(configDaten)
        print ("Configfile: ", self.configfilename, " schreiben OK")

    def modocConfigLesen(self):
        ####################################################################################
        ### Lese Variable aus Configfile modoc_conf.csv / im Problemfall setze Defaultwerte
        ### Alternativ gibts das makerbeam_conf.csv ... für den Makterbeam-Teststand
        ####################################################################################
        try:
            modocConfigfile = csv.reader(open(self.modocConfigfilename, "r"), delimiter=";")
        except FileNotFoundError:
            print ("ModocConfigfile: ", self.modocConfigfilename, " nicht gefunden!")

        configIdentifier = np.array([])
        configValue = np.array([])

        for spalte in modocConfigfile:
            configIdentifier = np.append(configIdentifier, spalte[0])
            configValue = np.append(configValue, spalte[1])

        AccessIndex = 0
        istFehlerfrei = True

        for identifier, value in self.modocKonstanten.items():
            if(configIdentifier[AccessIndex] == identifier):
                self.appBestimmendeMasse[identifier] = int(configValue[AccessIndex])
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
            modocConfigfile = csv.reader(open(self.modocConfigfilename, "w"), delimiter=";")
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
            ["temp_eich8", self.modocKonstanten["temp_eich8"]]
        )

        modocConfigfile.writerows(modocConfigDaten)
        print ("Configfile: ", self.modocConfigfilename, " schreiben OK")


class usbDataHandler:

    def __init__(self):
        self.data = np.array([])
        self.istFehlerfrei = True

        self.sim0 = 10
        self.sim1 = 600
        self.simtemp8 = 150

    def leseUSBline(self):

        self.istFehlerfrei = True
        self.data = np.array([])

        if usbsim:
            self.sim1 = self.sim1 + random.randint(-150,150)
            if self.sim1 < 10:
                self.sim1 = 800
            if self.sim1 > 1100:
                self.sim1 = 300
            i = random.randint(0,200)

            self.simtemp8 = self.simtemp8 + 1     # damit man einen Graphen hat, der ausserhalb des Messbereichs läuft
            self.simtemp8 = max (323, self.simtemp8)

            sim = np.array([
                4200-(self.sim0*4+i*9),    # 0
                8000000-(self.sim0+i)*5000,               # 1
                self.sim1,          #2
                random.randint(0,20), #3
                random.randint(1,10), #4
                random.randint(10,50), #5
                random.randint(40,90), #6
                random.randint(100,130), #7
                random.randint(120,150), #8
                random.randint(300,380),    #  9    das sind Werte für einen größeren Temperaturbereich
                random.randint(323,340),    # 10    das sind ADC Werte für 30oC bis  43oC
                random.randint(323,340),    # 11    das sind ADC Werte für 30oC bis  43oC
                random.randint(323,340),    # 12    das sind ADC Werte für 30oC bis  43oC
                0,0,0,0,0,0,0,              # 13..19
                0,0,0,0,0,0,0,0,0,0,        # 20..29
                0,0,0,0,0,1,1,1,1,1,        # 30..39
                0,0,                        # 40..41
                random.randint(323,340),    # 42    das sind ADC Werte für 30oC bis  43oC
                random.randint(323,340),    # 43    das sind ADC Werte für 30oC bis  43oC
                random.randint(323,330),    # 44    das sind ADC Werte für 30oC bis  43oC
                self.simtemp8])                  # 45    Testalternative für temp8: laufend steigernder Wert, der ausserhalb des Messbereichs läuft (siehe oben +1) geht aber erst hoch bei 323
            self.data = sim
            if self.sim0<200:
                self.sim0 += 5
            else:
                self.sim0 += 10
            if self.sim0 > 1000: self.sim0= 100
        else:

            try:
                eineUSBlinie = ser.readline().decode()
                dataStream = line.split(';')

                for element in dataStream:
                    if element == '':
                        istFehlerfrei = False
                        print("USB DataStream Fehler: Leeres Feld")

                if len(dataStream) != 48:
                    istFehlerfrei = False
                    print("USB DataStream Fehler: Länge ist " + len(dataStream))
                else:
                    if dataStream[46] != 'End':
                        istFehlerfrei = False
                        print("USB DataStream Fehler: Feld 46 nicht End, sondern: " + dataStream[46])

                if istFehlerfrei:
                    for element in dataStream:
                        if element == '':
                            element = '0'
                        self.data = np.append(self.data, abs(int(element)))

            except serial.serialutil.SerialException:
                istFehlerfrei = False
                print("USB DataStream Fehler: SerialException - Schlafe fuer 1 Sekunde")
                time.sleep(1)
            except:
                istFehlerfrei = False
                print("USB DataStream Fehler: Unbekannter Fehler")


root = Tk()
windowCanvas = Canvas(root, width=1600, height=1000)
windowCanvas.pack(fill=BOTH, expand=YES)

app = App(root, windowCanvas)
windowCanvas.bind("<Configure>", app.resizeCallback)
windowCanvas.pack(fill=BOTH, expand=YES)
app.appLoop()
