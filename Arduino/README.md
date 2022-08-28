# Notizen bezüglich Arduino

## 0. HX711 Verkabelung
```
  +-+
  +-+
 +---+
 |   |
 |   |
 |   |   4 pol Klinkenstecker
 |   |   (Farbe ist vom dünnen Drah des Klinkensteckerkabels)
 |   |
 +---+
  | |    GND (rot)

  | |    VCC (orange / weiß)

  | |    SCK - Clock (blau)

  |_|    DT - Data   (grün)
```

## 1. Drehmoment

```DiagMx[1] = (hx711a.read()/100.0-eichung1)/eichung2*eichung3;``` ... ergibt den Wert in Gramm


```102g = 1N   --> DiagMx[1]=DiagMx[1] / 102;```

- Da der Hebel aber nicht 1cm lang ist sondern am Makerbeam Teststand 58mm brauchen wir für Ncm -> ```DiagMx[1]=DiagMx[1] / 102 * 5,8```
- Da der Hebel aber nicht 1mm lang ist sondern am Makerbeam Teststand 58mm brauchen wir für Nmm -> ```DiagMx[1]=DiagMx[1] / 102 * 58```


```
DiagMx[1] = (hx711a.read()/100.0-eichung1)/eichung2*eichung3/102*58;
```

- Der 3S Testmotor mit 9x4,5 APC schafft 155Nmm dh 155Nmm bei 11.000Upm
- P = 2 x Pi x M/1000 x n/60  ...mit: Drehmoment M (Nmm); Drehzahl n (1/min); Leistung P (W); Pi = 3,14
- P = 6,28 x 0,155 x 183 -> 178W
- Benzinmotor mit 20Nm bei 7.000Upm: P = 6,28 x 20 x 116 -> 14.500W


## 2. Drehzahl
```
upmcalc = 0;
if (logg) Serial.print("upmcalc ");

for (ui = 1; ui <= 5; ui++)     // 5 mal Messen, dann wird es genauer
{
  upmpulse = pulseIn (upmpin, HIGH, 100000); // Timeout = 1/10 sec
  
  //  falsch    upmcalc += 6000000/upmpulse; 
  //            zb zeigt bei 1.210 Upm (Referenzmessung mit externem Drehzahlmesser) 
  //            der Arduino an: 4.200 als durchschnittlich um 3,5 zuviel
  //  falsch    upmcalc += 6000000/upmpulse;
  //            ... durchschnittlich um 4,37 zuviel


  // upmpulse ... Zeit zwischen einem Propellerblatt am Sensor vorbei
  //              bis zum Nächsten in Microsekunden = 1.000.000tel sec
  // 1000 U/Min mit 2-Blatt Prop 
  //  -> 2000 Impulse pro Minute 
  //  -> 33,3 Impulse pro Sec 
  //  -> upmpulse = 30.000
  // 1 U/Min mit 2-Blatt Prop 
  //  -> 2 Impulse pro Minute 
  //  -> 0,03 Impulse pro Sec 
  //  -> upmpulse = 30.000.000
  // 30.000.000 -> 1upm
  // dann wäre also upmcalc += 30000000/upmpulse; 
  //  -> 5x so hoch. Das ist aber noch mehr falsch

  // also erstmal laut Referenzmessung /3,5  -> 1714285
  // also erstmal laut Referenzmessung /4,37 -> 1371293

  if (logg) Serial.print("   "); 
  if (logg) Serial.print(1371293/upmpulse);
  upmcalc += 1371293/upmpulse;
}

if (logg) Serial.println(""); 

upmcalc = upmcalc / 5;
DiagMx[2] = upmcalc;
```

## 3. Schub

```DiagMx[3] = (hx711b.read()/100.0-eichung1)/eichung2*eichung3/102*58;```

## 4. Spannung
- Gemessen mit einem Spannungsteiler für 100V im Verhältnis 22:1 -> 4,3V
- Z-Diode mit 4,7V verhindert Spannungen >5V am Arduino

```DiagMx[4] = map(analogRead(spannungpin),0,5,0,115);```


## 5. Strom
- *ACHTUNG*: Das funktioniert nicht mit dem HX711, weil er auf E- GND hat und A- oder A+ auf GND liegen (wenn der 200A Shunt in der Akku-Minus-Leitung hängt - in der Akku-Plus-Leitung schon gar nicht, da liegen dann bis zu 60V am HX711)
- *ACHTUNG*: Es könnte nur so funktionieren, dass der HX711 potentialfrei arbeitet. Also mit einem separaten Akku und mit zwei Optokoppler für Data und Clock

Gemessen mit 200A Shunt (liefert bei 200A -> 75mV) und einem HX711
Mit vier Widerständen den Wiegesensor nachgebaut, der Shut liefert dann die Differenzspannung zwischen A- und A+ die der HX711 misst.
- E+ E- A+ A- auf HX711 (wie beim Wiegesensor)
- A- vom Akku-Minus = Arduino-GND
- A+ zum ESC-Minus
- Alle 4 Widerstände "R" normale 1KOhm Typen (entspricht Ohmsche Werte vom Wiegesensor)

```
       +-------------+----( E+
       |             |
      +-+           +-+
      |R|           |R|
      | |           | |
      +-+           +-+
       |             |
       |  +-------+  |
 A- )--+--| Shunt |--+----( A+
       |  +-------+  |
       |             |
      +-+           +-+
      |R|           |R|
      | |           | |
      +-+           +-+
       |             |
       +-------------+----( E-
```

- ```DiagMx[5] = (hx711c.read()/1.0-eichungs1)/eichungs2*100;``` der /1.0 ist nötig, da sonst die Berechnung nicht mit Gleitkomma erfolgt. float hilft nix !
- ```DiagVx[5] = constrain(map(DiagMx[5],1,DiagMm[5],Diagymax,Diagymin),Diagymin,Diagymax);```

Einfacher gehts mit dem ACS709 75A Stromsensor, der MUSS aber einigemale hintereinander messen und Durchschnitt bilden, da sonst zu große Schwankungen durch den ESC

```
strom = 0;
for (i=0; i<10; i++)
   strom = strom + analogRead(spannungpin);
strom = strom / 10;
strom = (516-strom) / 3.68;
DiagMx[5] = strom * 100;    // kommt ja als hA (Hundertstel Amper) zur Anzeige
```

## 6. Temperatur
```
  +---------------( +5V
  |           
 +-+          
 |R| 4100 Ohm
 | |          
 +-+          
  |
  +--------------- Analog tempXpin
  |            
 +-+           
 |R| Platin-Chip-Temperatursensor PCA 1.2010.10  -70 bis +350oC
 | |   Nennwiderstand 1.000 Ohm / Meßstrom max 1mA
 +-+   
  |            
  +----------------( Masse
```

Messwerte mit Ohmmeter:
|  oC |  Ohm |
| --- | ---- |
| -12 |  934 |
|   5 | 1050 |
|  35 | 1100 |
| 100 | 1390 |

Temperaturkoffizient a = 3,85 x 0,001 x oC ... lt. Datenblatt
Widerstand(T) = Widerstand(20oC) * ( 1 + a * (T - 20oC) ) ...laut Wikipedia

Geht man statt von 20oC vom Meßpunkt 35oC aus und berechnet den Widerstand(T), dann gibts nur geringe Abweichungen (mit weiteren berechneten Datenpunkten für 0, 200, 300 und 400):

|  oC |  Ohm |
| --- | ---- |
| -12 |  901 |
|   5 |  973 |
|  35 | 1100 |
| 100 | 1375 |
|   0 |  952 |
| 200 | 1799 |
| 300 | 2222 |
| 400 | 2646 |

Geht man von minimalen Widerstandswert 900 Ohm aus und 1mA Meßstrom fällt 0,9V am Temperaursensor ab, d.h. 4,1V am Widerstand gegen +5V oder 4100 Ohm. Damit ergibt sich eine zu messende Spannung von 0,9V (-12oC) und 1,96V (400oC)
