# Notizen bezüglich Arduino

## 1. Drehmoment

```DiagMx[1] = (hx711a.read()/100.0-eichung1)/eichung2*eichung3;``` ... ergibt den Wert in Gramm


```102g = 1N   --> DiagMx[1]=DiagMx[1] / 102;```

- Da der Hebel aber nicht 1cm lang ist sondern am Makerbeam Teststand 58mm brauchen wir für Ncm --> ```DiagMx[1]=DiagMx[1] / 102 * 5,8```


