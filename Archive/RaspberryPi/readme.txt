### Autostart des Python Programms fuer MoDoc ###
#################################################

In /home/pi/.config/autostart gibts das fks01startup.py
Dieses wird automatisch gestartet nach dem booten und fuehrt aus..
Exec=python3.6 /home/sp/fks01startup.py

Die Zeile Path = /home/sp .... ist vielleicht gar nicht funktionierend, muessen wir nochmal testen

In /home/sp gibts das fks01startup.py
Dieses File hat den gleichen Namen wir das in autostart, ist aber kein Batchfile, sondern der Pythonsource selbst.
Der Source selbst ist eine Kopie des aktuellen Sources (also von e8a.py oder neuer) - jedoch mit dem fixen Namen fks01startup.py

Startet man das File manuell, dann oeffnet sich der Python Entwicklershell Thonny.
Dort kann man den Source editieren und ausfuehren.

### Uhr einstellen ###
######################

Terminal
sudo date --set '2020-01-19 08:57'

### USB Stick mounten ###
#########################

Das mounten über Befehle /etc/stab etc hat nicht funktioniert,
daher "einfach" gelöst: 
File Manageger / Edit / Preferences
Volume Management 
... hier das Hackerl weggenommen bei "Show available options.."
Nun kommt beim Einstecken des Memorysticks nix daher
und der Stick ist schnell sichtbar in /media/pi/MODOC
(der Stick muss die Bezeichnung MODOC haben, denn den überprüfe ich 
im Bash-Script. Hab den am Mac mit Festplattendienstprogramm festgelegt).
