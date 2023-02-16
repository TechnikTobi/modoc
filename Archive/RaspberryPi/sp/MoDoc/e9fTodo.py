user = "sp"
raspvers = "e9a"
arduvers = 0

rasp = 0                        # 1.. Betrieb am Raspberry (Port und Pfad für Configdateien) / 0.. Betrieb am Mac
usbsim = 1                      # 1.. statt Daten von USB zu lesen werden Messwerte simuliert für Tests ohne Arduino
if rasp == 1: usbsim = 0
adcdirekt = 0                   # 2.. Temperatur1..8: der digitale Wert des ADC (0...1023) wird angezeigt OHNE Umrechnung auf oC
                                # 1.. detto mit Berücksichtigung von temp_eich ab config_modoc.csv
                                # 0.. Skalierter Wert für oC
prüfstand = 1                   # 1.. Prüfstand / 0.. Makerbeam-Test-Aufbau bei SP
logg = 1                        # 1.. looging von Meldungen
LowSamplingGrenze = 1           # wenn mehr als 10x hintereinander die Samplingrate kleiner ist, dann auomatisch Restart
EH_Schub = 1                    # 1 .. kg, 1000 .. g

if not (usbsim): import RPi.GPIO as GPIO

# Kalibrierugskonstanten
drehmoment_kal = 0
schub_kal = 0

if rasp: fontsizefaktor = 0.7
else:    fontsizefaktor = 1.0

MesswertAnzahl = 15             # nötig für History/Array-berechnung
History = 50                   # Anzahl der historisch im Graphen darzustellender Werte

MaxAnzVerschiedeneGraphen = 1   # Das ist die Anzahl der Koordinatenbereiche
graphenLegendenHoehe = 50            # Platz in Y-Richtung für Legende bei jedem einzelnen Graphan

arduinoUSBstartpin = 11                     # Pin für Kabel zum Arduino "ready für USB - Datenübernahme" ... logisch: GPIO17
                                            # Pin 11 ist die physikalische Pinordnung und dort ist der logische Pin: GPIO17
if not (usbsim):
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(arduinoUSBstartpin, GPIO.OUT)
    GPIO.output(arduinoUSBstartpin, GPIO.LOW)  # sofort mal auf Off setzen

Glättung = 10



#######################################################
### Setze Variablen, die man im GUI noch verändern kann
#######################################################
def GUIReset():
    global grx1
    global grx2
    global gry1
    global gry2
    global grh
    global graphenLegendenHoehe
    global grAchsenDicke
    global grHilfslinienDicke
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
    ###########
    # Begriffe
    ###########
    # Dock .... unterer vertikaler Bereich für Buttons u a Steuerfelder des GUI
    # Rund .... Rundinstrumente - Messwerte sind durch einen Zeiger dargestellt / nur 1 Messswert je Rundinstrument
    # WG ...... Wertegruppen - zeigen Messwerte nummerisch an / mehrere Messwerte untereinander
    # GR ...... Graphische Liniendarstellung auf Achsen / auch mehrere Messwerte in einem Graph möglich

    # fensterBreiteAufteilungWertegruppenRundinstrumente .. Prozentuale Teilung des Bildschirms in der Breite zwischen Graph und Wertegruppen bzw Rundinstrumente
    # fensterHoeheAufteilungWertegruppenRundinstrumente ... Prozentuale Teilung des Bildschirms in der Höhe zwischen Wertegruppen und Rundinstrumente

    ##################################
    # Bildschirmaufteilung generell
    ##################################
    #
    #       fensterBreiteAufteilungWertegruppenRundinstrumente --> #
    ##################################
    #                  # WG1    WG2  #
    # Graph1           # WG3    WG4  #  fensterHoeheAufteilungWertegruppenRundinstrumente
    #                  # WG5    WG6  #  V
    # Graph2           ###############  #
    #                  # Rund1 Rund2 #
    # Graph x          #             #
    #                  # Rund3 Rund4 #
    ##################################
    #             Dock               #
    ##################################

    # Dock:  links oben:   x= rand   y= fensterHoehe - dockh - rand
    #        rechts unten: x= fensterBreite    y= fensterHoehe


    # Graph: links oben:   x= rand               y= rand
    #        rechts unten: x= grx2= 2/3 von fensterBreite  y= docky1


    grx1= rand * 6      # damit genug Platz für die Hilfslinen Labels
    gry1= rand
    grx2= fensterBreite/100*fensterBreiteAufteilungWertegruppenRundinstrumente
    gry2= docky1-rand
    grh= (gry2-gry1)/MaxAnzVerschiedeneGraphen - rand - graphenLegendenHoehe

    grAchsenDicke= 2
    grHilfslinienDicke= 1
    grXsampling= (grx2-grx1)/History
    grLinienDicke= 3

    # Wertegruppen: links oben:   x= grx2    y= rand
    #               rechts unten: x= fensterBreite     y= wgy2= 1/3 von (fensterHoehe minus dock)

    wgx1= grx2+rand
    wgy1= rand
    wgx2= fensterBreite-rand
    wgy2= docky1/100*fensterHoeheAufteilungWertegruppenRundinstrumente
    wgwertfont="fixedsys"
    #    wgwertsize= int((wgy2-wgy1)/30)
    wgwertsize= int((wgy2-wgy1)/MaxAnzWertegruppen/2.2)
    wgwertabstand= wgwertsize*2

    # Rundinstrumente: links oben:   x= grx2    y= wgy2
    #                  rechts unten: x= fensterBreite     y= docky1
    rundx1= grx2+rand
    rundy1= wgy2+rand
    rundx2= fensterBreite-rand
    rundy2= docky1-rand


    # Diese Radiusberechnung gilt für 3 Rundinstrumente nebeneinander (und nur 1 Reihe)
    # hinsichtlich Breite: verfügbare Breite - innere Ränder (zw 1. und 2., zw 2. und 3.) / 3 Rundinstrumente  ... Radius=Druchmesser/2
    # hinsichtlich Höhe: verfügbare Höhe /2
    # tatsächerlicher Radius ist kleinerer Wert, von der möglichen Größe hinsichtlich Breite und Höhe



#########################
### Globaler Programmtext
#########################



# Messwertmin/max definiert physische Grenzwerte, die auch im GUI dargestellt werden sollen (Rundinstrument - Skala, Graph-Y-Achsengröße)
# YAchsemin/max definiert die aktuellen min/max Werte auf der Y Achse, die kleiner sein können, wenn aufgrund geringer Messwertschwankungen in den Bereich hineingezoomt wird
#   der Wert ist für alle Messwerte die den gleichen WErt Graphpos haben identisch

# Graphpos definiert ob ein Messwert gar nicht in einem Graphen dargestellt wird (Wert = 0) oder ob er im x.ten Graphen vorkommen soll (Wert = x)
#  haben mehrere Messwerte den gleichen Graphpos-Wert, dann werden diese Messwerte GEMEINSAM in einem Graphen dargestellt
# Es gibt max 4 Graphen mit je max 10 Messwerten
# MaxAnzGraphen = 10
# MaxAnzVerschiedeneGraphen = 4
Graphenlinie = False


# Jeder Graph bzw Messwert wird in einem Achsenkreuz dargestellt. Alle Mesßwerte, die bei Graphpos[] den gleichen Wert haben werden im GLEICHEN Achsenkreuz dargestellt.
# Jedes Achsenkreuz darf nur 1x gezeichnet und nur 1x gelöscht werden. Den eines Achsenkreuzes erkennt man im Array...

AchsenkreuzSichtbar = np.array([0,                  # Wert für Index 0 ist nur Platzhalter
                                0,                  # für 1.tes Achsenkreuz (also wenn Graphpos[] = 1 ist)  0... Achsenkreuz ist aktuell NICHT dargestellt (noch nicht oder aktuell gelöscht)
                                                    #                                                       1... Achsenkreiz ist aktuell dargestellt
                                0, 0, 0])           # für 2.tes bis 4.tes Achsenkreuz

# Anzahl der Messwerte pro Achsenkreuz

PosMesswertProAchsenkreuz = np.array([0,0,0,0,0,0,0,0,0,0,0,0,0,0,0])      # Nummer jedes Messwertes pro Achsenkreuz (also zb bei 1ten Achsenkreuz... 1,2,3, beim 2th Acchsenkreuz... 1,2 )
for j in range (0, MaxAnzVerschiedeneGraphen+1):
    z = 1
    for i in range (0, MesswertAnzahl):
        if Graphpos[i] > 0:
            if Graphpos[i] == j:
                PosMesswertProAchsenkreuz[i] = z
                z = z + 1

if rasp:
    PORT = '/dev/ttyACM0' # fuer Raspberry
else:
#    PORT = '/dev/tty.usbmodem1421' # fuer Mac
    PORT = '/dev/tty.usbmodem1411' # fuer Mac


wd=math.pi/2
wi=math.pi*0.2

lasttime = 0
lasttimezoomim = time.time()

class c_Graph:

    def __init__(self, Graphindex, eingabePosX1, eingabePosX2, eingabePosY1, eingabePosY2):

    def setGraphColorScheme(self, istTag):
        self.hilfslinien.setHilfslinienColorScheme(istTag)


    def updateGraph(self, MesswertNr):

        if self.LabellinieGezeichnet:
            windowCanvas.delete(self.Labellinie)


        xlabellinie = rand*10 + int((self.posx2 - self.posx1 - rand*10 ) / (MesswertProAchsenkreuz[Graphpos[MesswertNr]] + 1)) * (PosMesswertProAchsenkreuz[MesswertNr])        # X Abstand für die Labellinie

        for i in range (0, int(dataGraph.size/MesswertAnzahl-1)):

            if x1 >= xlabellinie:           # Labellinie zeichnen, wenn man mit der dataLinie eben im Bereich links/rechts der Labellinie ... in X Richtung ist
                if x2 <= xlabellinie:
                    p = (xlabellinie-x2)/(x1-x2)                                                                                                                # Interpolation der Y-Koord der Labellinie, weil man ja irgendwo auf die Linie trifft
                    ylabellinie = y2 - p * (y2-y1)
                    self.Labellinie = windowCanvas.create_line(xlabellinie, self.posy1+graphenLegendenHoehe, xlabellinie, ylabellinie, fill= "black", width= grLinienDicke)
                    self.LabellinieGezeichnet = True


class App:
    def __init__(self, root):

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


        #        logoimg = Image.open("Logo.tiff")
        #        logofilename = ImageTk.PhotoImage(logoimg)
        #        canvas = Canvas(root, width=fb*0.315, height=fensterHoehe*0.3)
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
### Kalibrieren Drehmoment und Schub (Fenster)
####################################
    def Kalibrieren(self):

        global wKalTextfeld
        global wKal
        global KalKeyInfont
        global KalKeyInsize
        global wKalh

        wKalb = fensterBreite/2
        wKalh = fensterHoehe/6
        KalKeyInfont="fixedsys"
        KalKeyInsize= int(wKalh/8 * fontsizefaktor)
        wKalx1 = (fensterBreite-wKalb)/2
        wKaly1 = (fensterHoehe-wKalh)*0.3
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

###############################################
### Zeige Alarmmeldung an
###############################################
    def Alarmanzeige(self, alarmtext):
        alarmfont="courier"
        alarmsize= int(fensterHoehe/15)

        Alarm1 = Label(root, text=alarmtext, bg=self.farbeAlarmBackground, fg=self.farbeAlarmForeground,font=(alarmfont, alarmsize))
        Alarm1.pack()
        Alarm1.place(x=fensterBreite/2, y=fensterHoehe/2, anchor="center")


###############################################
### Lese USB ein und stelle alle Datenwerte dar
###############################################
    def LeseUSB(self):
        global wi
        global LabelWert11
        global DockWert11
        global DockWert12
        global werti
        global dataGraph
        global LowSamplingGrenze
        global wEingabeglättung
        global lastfbteil
        global lastfhteil
        global lastglättung
        global data
        global usbdatenok
        global EH_Schub
        global Glättung

        First= True
        ErsterMesswert= True
        Startup= False
        LowSampling= 0
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

        datag  = [0 for x in range(45)]

        while True:
            global lasttime
            global lasttimezoomim
            global dataRundinstrument

            DockWert13.config(text = "Benutzer: " + user)

            if prüfstand: DockWert14.config(text = "")
            else:         DockWert14.config(text = "MakerBeam-Eichung!")

            Glättung= wEingabeglättung.get()
            if Glättung != lastglättung:
                lastglättung = Glättung
                GUIReset()
                self.AnzeigeObjekteReset()


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
                i = 1
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

                # Bestimmung CPU Temperatur
                if rasp:
                    data[28] = 99
                else: datag[14]= 99
                datag[14] = data[28]                   # vorläufig, da dzt noch nicht konfigurierbar, welche Messwerte angezeigt werden sollen und max 9

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
                    self.AnzeigeObjekteReset()

                if taste4 == 0:                     # Tag/Nacht Design umschalten
                    DesignKeyIn()


                if dataGraph.size >= History * MesswertAnzahl:
                    dataGraph = np.delete(dataGraph, ([0]), axis=0)   # lösche ältersten Messwert

                    # Achse re-skalieren: zoom-out (Messwerte werden größer)
                if datag[12] > YAchsemax[13]:                   # testweise mal für Temp8 # Hier muss noch programmiert werden, dass zoom-out jeweils pro Achsenkreuz separat läuft
                    for i in range (0, MesswertAnzahl):
                        if Graphpos[i] == Graphpos[13]:
                            YAchsemax[i] = int(YAchsemax[i] * 1.2)  # mal 20% größer
                    self.AnzeigeGraphenReset()
