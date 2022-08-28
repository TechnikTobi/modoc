# Notizen bezüglich Arduino

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




