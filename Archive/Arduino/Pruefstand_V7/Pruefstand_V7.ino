#include <SPI.h>
#include <Q2HX711.h>#
#include <Servo.h>
#include <Adafruit_NeoPixel.h>

// Zeigt Informationen mit Serial.print an  HINWEIS: Fehlermeldungen werden immer ausgegeben
#define logg false

// Gibt die Datenwerte permanent mit Serial.print aus für Echtzeitanzeige am PC/Mac
#define stream true

Servo vpwm;  // Verbrenner-Gasservo
Servo epwm;  // Elektro-ESC-Steller

// ######################
// ### HTX711 Verkabelung
// ######################
//
//    +-+
//    +-+
//   +---+
//   |   |
//   |   |
//   |   |   4 pol Klinkenstecker
//   |   |   (Farbe ist vom dünnen Drah des Klinkensteckerkabels)
//   |   |
//   +---+
//    | |    GND (rot)
//
//    | |    VCC (orange / weiß)
//
//    | |    SCK - Clock (blau)
//
//    |_|    DT - Data   (grün)

// ***** Pindefinitionen *****
// PWM
#define rckanal1          13 // zusätzlich GND (neben 13)
#define rckanal2          12 // --"--
#define rckanal3          11 // --"--
#define vpwmpin           10 // 3pol Buchse mit 5V, GND 
#define epwmpin            9 // 3pol Buchse mit 5V, GND

//  Digital
#define upmpin            22   // 3pol Buchse mit 5V, GND
#define offbutton           23
#define vccrelaispin      24   // direktes Kabel 
#define taste1              25 // zusätzlich GND Buchse
#define taste2              27 // --"--
#define taste3              29 // --"--
#define taste4              31 // --"--
#define notaus            26   // 2pol Buchse mit GND
#define usbstart          28
#define hx711a_data_pin     33 // 2pol Buchse für a (Drechmoment) weitere Buchse 5V, GND
#define hx711a_clock_pin    35 // --"--
#define hx711b_data_pin     37 // 2pol Buchse für b (Schub) weitere Buchse 5V, GND
#define hx711b_clock_pin    39 // --"--
#define neoled1pin          41 // Kabel..

//  Analog
#define temp1pin          A4 // zusätzlich GND Buchse
#define temp2pin          A5 // --"--
#define temp3pin          A6 // --"--
#define temp4pin          A7 // --"--

#define strompin          A8
#define spannungpin       A9

#define vgaspotipin      A10
#define egaspotipin      A11

#define vccspannung      A12


// Diverse Variable
int i;
int j;
int ui;
int xi;
int y1;
int li;
int yinc;   
int limax; 
int y1last;
int y2;
int y2last;
int hor;
int ver;
int temp1;
unsigned long upmpulse;
float upmcalc;
char readbuf;
String readspalte;
int readint;
float strom;

int idle = 850;
//  850 --> ca +60°
// 1500 --> ca   0°
// 2200 --> ca -60°


// für Messwerte
int Mx[50];      // Aktueller Messwert ohne Umrechnung

// für HX711 - Drehmoment
long int eichung1 = 84435;
long int eichung2 = 15178;
long int eichung3 = 743;
long int drehm;

// für HX711 - Strom
long int eichungs1 = 8392336;
long int eichungs2 = 232255;

Q2HX711 hx711a(hx711a_data_pin, hx711a_clock_pin); //Drehmoment
Q2HX711 hx711b(hx711b_data_pin, hx711b_clock_pin); //Schub

#define NUMPIXELS  1    // How many NeoPixels are attached to the Arduino?
Adafruit_NeoPixel pixels = Adafruit_NeoPixel(NUMPIXELS, neoled1pin, NEO_GRB + NEO_KHZ800);

void setup() 
{
  Serial.begin(9600);

  if (logg) Serial.print("Start setup... ");

  pinMode(upmpin,    INPUT);
  pinMode(rckanal1,  INPUT);
  pinMode(rckanal2,  INPUT);
  pinMode(rckanal3,  INPUT);
  pinMode(offbutton, INPUT_PULLUP);
  pinMode(taste1,    INPUT_PULLUP);
  pinMode(taste2,    INPUT_PULLUP);
  pinMode(taste3,    INPUT_PULLUP);
  pinMode(taste4,    INPUT_PULLUP);
  pinMode(notaus,    INPUT_PULLUP);
  pinMode(usbstart,  INPUT);

  pinMode(vccrelaispin, OUTPUT);
  digitalWrite(vccrelaispin, HIGH); // beim Starten des Arduinos soll der zweite PNP Transistor sperren (das macht er auch ohne HIGH auf diesem Kabel), damit bleibt der erste PNP Transitor leitend und das Relais bleibt angezogen

  vpwm.attach(vpwmpin);
  epwm.attach(epwmpin);
  vpwm.writeMicroseconds(idle);             
  epwm.writeMicroseconds(idle);

  pixels.begin(); // This initializes the NeoPixel library.  
  pixels.setPixelColor(0, pixels.Color(0,0,20)); pixels.show();  // Grün, Rot, Blau

  if (logg) Serial.print("...setup fertig");
}

void loop() 
{
  i = 0;
  xi = 1;

  do
  {
    upmcalc = 0;
    for (ui = 1; ui <= 5; ui++)     // 5 mal Messen, dann wird es genauer
      {
        upmpulse = pulseIn (upmpin, HIGH, 100000); // Timeout = 1/10 sec ,, das wären also minimum von 600Upm
        // upmpulse ... Zeit zwischen einem Propellerblatt am Sensor vorbei bis zum nächsten in Microsekunden = 1.000.000tel sec
        // 1000 U/Min mit 2-Blatt Prop -> 2000 Impulse pro Minute -> 33,3 Impulse pro Sec -> upmpulse = 30.000
        // 1 U/Min mit 2-Blatt Prop -> 2 Impulse pro Minute -> 0,03 Impulse pro Sec -> upmpulse = 30.000.000
        // 30.000.000 ->  1 upm
        // dann wäre also    upmcalc += 30000000/upmpulse; --> 5x so hoch. Das ist aber noch falscher.
        // also erstmal laut Referenzmessung /3,5  --> 1714285
        // also erstmal laut Referenzmessung /4,37 --> 1371293
        upmcalc += 1371293/upmpulse;
      }
    upmcalc = upmcalc / 5;
    Mx[1] = upmcalc;
//    Mx[2] = hx711a.read(); // Drehmoment
    Mx[2] = (hx711a.read()/100.0-eichung1)/eichung2*eichung3/102*58;
    
    Mx[3] = hx711b.read(); // Schub
    // 4 ... erst am Raspberry: Ausgangsleistung
    Mx[5] = analogRead(spannungpin); // Spannung
    Mx[6] = analogRead(strompin);    // Strom
    // 7 ... erst am Raspberry: Eingangsleistung
    // 8 ... erst am Raspberry: Wirkungsgrad
    Mx[9] = 1; // Spritverbrauch
    Mx[10] = analogRead(temp1pin); // Temp1
    Mx[11] = analogRead(temp2pin); // Temp2
    Mx[12] = analogRead(temp3pin); // Temp3
    Mx[13] = analogRead(temp4pin); // Temp4
    // 14 ... erst am Raspberry: Delta-Max
    Mx[15] = analogRead(vgaspotipin); // Gaspoti auf V-Box
    Mx[16] = analogRead(egaspotipin); // Gaspoti auf E-Box
    // 17 ... erst am Raspberry: Gas-Programm
    Mx[18] = pulseIn(rckanal1, HIGH, 20000); // RC-K1 (Gas)
    Mx[19] = pulseIn(rckanal2, HIGH, 20000); // RC-K2
    Mx[20] = pulseIn(rckanal3, HIGH, 20000); // RC-K3
    Mx[21] = 1; // RTC (Datum)
    Mx[22] = 1; // RTC (Zeit)
    Mx[23] = 1; // Temperatur Aussen
    Mx[24] = 1; // Feuchtigkeit
    // 25 ... erst am Raspberry: Meßdauer
    Mx[26] = 1; // Schallpegel
    Mx[27] = 1; // Vibration
    Mx[28] = analogRead(vccspannung); // VCC 3S Lipo
    // 29 ... erst am Raspberry: TempCPU
    // 30 ... erst am Raspberry: Motor
    // 31 ... erst am Raspberry: Propeller
    // 32 ... erst am Raspberry: Akku
    // 33 ... erst am Raspberry: Sprit
    // 34 ... erst am Raspberry: Einstellungen
    // 35 ... erst am Raspberry: Bemerkungen
    Mx[36] = digitalRead(offbutton); // Austaster
    Mx[37] = digitalRead(taste1); // Taste1
    Mx[38] = digitalRead(taste2); // Taste2
    Mx[39] = digitalRead(taste3); // Taste3
    Mx[40] = digitalRead(taste4); // Taste4
    Mx[41] = digitalRead(notaus); // NotAusTaste
        
    if (stream && digitalRead(usbstart)==HIGH)
    {
      // Wenn stream gesetzt ist Werte am USB ausgeben
      pixels.setPixelColor(0, pixels.Color(0,0,0)); pixels.show();  // Grün, Rot, Blau
      for (i = 1; i<=41; i++)
      {
        Serial.print(Mx[i]);
        Serial.print(";");
      }
      Serial.print("End");
      Serial.println(";");
      pixels.setPixelColor(0, pixels.Color(0,0,20)); pixels.show();  // Grün, Rot, Blau
    }

    if (Mx[36] == LOW) // Off-Button gedrückt
    {
      if (logg) Serial.print("Off-Button gedrückt - starte Shutdown...");
      for (i= 0; i<100; i++) // Delay 20 sec
      {
        pixels.setPixelColor(0, pixels.Color(0,30,0)); pixels.show();  // Grün, Rot, Blau
        delay (100);
        pixels.setPixelColor(0, pixels.Color(0,0,0)); pixels.show();  // Grün, Rot, Blau
        delay (100);
      }
      pixels.setPixelColor(0, pixels.Color(0,255,0)); pixels.show();  // Grün, Rot, Blau
      delay (2000);
  
      digitalWrite(vccrelaispin, LOW);  // mit LOW auf diesem Kabel schaltet der zweite PNP Transistor durch, damit sperrt der erste PNP Transistor und das Relais fällt ab
    }

  } while (true);
}

     
/*
// ######################
// ### 1.. Drehmoment ###
// ######################

  // DiagMx[1] = (hx711a.read()/100.0-eichung1)/eichung2*eichung3;  // das sind mal Gramm
  // 102g = 1N   --> DiagMx[1]=DiagMx[1] / 102;
  // Da der Hebel aber nicht 1cm lang ist sondern am Makerbeam Teststand 58mm brauchen wir für Ncm --> DiagMx[1]=DiagMx[1] / 102 * 5,8
  // Da der Hebel aber nicht 1mm lang ist sondern am Makerbeam Teststand 58mm brauchen wir für Nmm --> DiagMx[1]=DiagMx[1] / 102 * 58

  DiagMx[1] = (hx711a.read()/100.0-eichung1)/eichung2*eichung3/102*58;

  // der 3S Testmotor mit 9x4,5 APC schafft 155Nmm dh 155Nmm bei 11.000Upm
  // P = 2 x Pi x M/1000 x n/60  ...mit: Drehmoment M (Nmm); Drehzahl n (1/min); Leistung P (W); PI = 3,14
  // P = 6,28 x 0,155 x 183 --> 178W

  // Benzinmotor mit 20Nm bei 7.000Upm
  // P = 6,28 x 20 x 116 --> 14.500W

// ####################
// ### 2.. Drehzahl ###
// ####################

  upmcalc = 0;
//   if (logg) Serial.print("upmcalc ");

  for (ui = 1; ui <= 5; ui++)     // 5 mal Messen, dann wird es genauer
  {
    upmpulse = pulseIn (upmpin, HIGH, 100000); // Timeout = 1/10 sec
    // falsch    upmcalc += 6000000/upmpulse; zb zeigt bei 1.210 Upm (Referenzmessung mit externem Drehzahlmesser) der Arduino an: 4.200 als durchschnittlich um 3,5 zuviel
    // falsch    upmcalc += 6000000/upmpulse;... durchschnittlich um 4,37 zuviel

    // upmpulse ... Zeit zwischen einem Propellerblatt am Sensor vorbei bis zum nächsten in Microsekunden = 1.000.000tel sec
    // 1000 U/Min mit 2-Blatt Prop -> 2000 Impulse pro Minute -> 33,3 Impulse pro Sec -> upmpulse = 30.000
    // 1 U/Min mit 2-Blatt Prop -> 2 Impulse pro Minute -> 0,03 Impulse pro Sec -> upmpulse = 30.000.000
    // 30.000.000 ->  1 upm
    // dann wäre also    upmcalc += 30000000/upmpulse; --> 5x so hoch. Das ist aber noch falscher.

    // also erstmal laut Referenzmessung /3,5  --> 1714285
    // also erstmal laut Referenzmessung /4,37 --> 1371293

//   if (logg) Serial.print("   "); if (logg) Serial.print(1371293/upmpulse);
    upmcalc += 1371293/upmpulse;
  }
  if (logg) Serial.println(""); 
  
  upmcalc = upmcalc / 5;
  DiagMx[2] = upmcalc;

// #################
// ### 3.. Schub ###
// #################

  DiagMx[3] = (hx711b.read()/100.0-eichung1)/eichung2*eichung3/102*58;

// ####################
// ### 4.. Spannung ### 
// ####################
  // Gemessen mit einem Spannungsteiler für 100V im Verhältnis 22:1 --> 4,3V
  // Z-Diode mit 4,7V verhindert Spannungen >5V am Arduino
  //
  //        +-------------( vom Akku-Plus
  //        |  
  //      +---+ 
  //      |22k| 
  //      |   | 
  //      +---+ 
  //        |
  //        +---------+---( zum Arduino spannungpin
  //        |         |
  //      +---+    /--+--
  //      |1k |   /  / \  4,7V
  //      |   |     /   \ Z-Diode 
  //      +---+    +-----+ 
  //        |         |
  //        +---------+---( vom Akku-Minus = Arduino-GND


  DiagMx[4] = map(analogRead(spannungpin),0,5,0,115);

// #################
// ### 5.. Strom ###
// #################
  // ACHTUNG
  // ACHTUNG: das funktioniert nicht mit dem HX711, weil er auf E- GND hat und A- oder A+ auf GND liegen (wenn der 200A Shunt in der Akku-Minus-Leitung hängt - in der Akku-Plus-Leitung schon gar nicht, da liegen dann bis zu 60V am HX711)
  // ACHTUNG: es könnte nur so funktionieren, dass der HX711 potentialfrei arbeitet. Also mit einem separaten Akku und mit zwei Optokoppler für Data u Clock
  //
  // Gemessen mit 200A Shunt (liefert bei 200A -> 75mV) und einem HX711
  // Mit vier Widerständen den Wiegesensor nachgebaut, der Shut liefert dann die Differenzspannung zwischen A- und A+ die der HX711 misst.
  //   E+ E- A+ A- auf HX711 (wie beim Wiegesensor)
  //   A- vom Akku-Minus = Arduino-GND
  //   A+ zum ESC-Minus
  //   Alle 4 Widerstände "R" normale 1KOhm Typen (entspricht Ohmsche Werte vom Wiegesensor)
  //
  //       +-------------+----( E+
  //       |             |
  //      +-+           +-+
  //      |R|           |R|
  //      | |           | |
  //      +-+           +-+
  //       |             |
  //       |  +-------+  |
  // A- )--+--| Shunt |--+----( A+
  //       |  +-------+  |
  //       |             |
  //      +-+           +-+
  //      |R|           |R|
  //      | |           | |
  //      +-+           +-+
  //       |             |
  //       +-------------+----( E-

//  DiagMx[5] = (hx711c.read()/1.0-eichungs1)/eichungs2*100;       // der /1.0 ist nötig, da sonst die Berechnung nicht mit Gleitkomma erfolgt. float hilft nix !
//  DiagVx[5] = constrain(map(DiagMx[5],1,DiagMm[5],Diagymax,Diagymin),Diagymin,Diagymax);


  // Einfacher gehts mit dem ACS709 75A Stromsensor, der MUSS aber einigemale hintereinander messen und Durchschnitt bilden, da sonst zu große Schwankungen durch den ESC

  strom = 0;
  for (i=0; i<10; i++)
     strom = strom + analogRead(spannungpin);
  strom = strom / 10;
  strom = (516-strom) / 3.68;
  DiagMx[5] = strom * 100;    // kommt ja als hA (Hundertstel Amper) zur Anzeige

// #################
// ### 6.. Temp1 ###
// ### 7.. Temp2 ###
// ### 8.. Temp3 ###
// ### 9.. Temp4 ###
// #################

  DiagMx[6] = map(analogRead(temp1pin),539,647,27,200);
  DiagMx[7] = map(analogRead(temp2pin),539,647,27,200);
  DiagMx[8] = map(analogRead(temp3pin),539,647,27,200);
  DiagMx[9] = map(analogRead(temp4pin),539,647,27,200);
 */
 
