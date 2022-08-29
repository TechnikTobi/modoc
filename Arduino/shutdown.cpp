#include "libs/modoc/pins.hpp"

#include "neoled_helper.hpp"
#include "shutdown.hpp"

void shutdown(Adafruit_NeoPixel* neoLED) {

	// Warten bis Raspberry heruntergefahren ist
	// Durch das Herunterfahren des RPi wird auch dessen
	// GPIO Pin potentialfrei und ist nicht mehr auf HIGH
	while (digitalRead(Pin::Digital::USBstart) == HIGH) {
		NeoLED::setColor(
			neoLED,
			0,
			30, 0, 0
		);
		delay(200);
		NeoLED::clear(neoLED, 0);
		delay(200);
	}

	// Schnell blinken um zu signalisieren dass RPi aus ist
	// und finale shutdown Phase eingeleitet wird
	for(int blink_step = 0; blink_step < 20; blink_step++) {
		NeoLED::setColor(
			neoLED,
			0,
			255, 0, 0
		);
		delay(50);
		NeoLED::clear(neoLED, 0);
		delay(50);
	}

	// Setze diesen Pin LOW damit der zweite PNP Transistor 
	// durchschaltet, wodurch der erste PNP Transistor sperrt
	// und das Relais abfällt
	digitalWrite(Pin::Digital::VCCrelai, LOW);

}
