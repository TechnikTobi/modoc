#include <SPI.h>

#include "libs/AdafruitNeoPixel/Adafruit_NeoPixel.h"

// Need to include .cpp file for implementation of class functions/constructor/...
#include "libs/HX711/Q2HX711.cpp"

#include "libs/modoc/pins.hpp"

#include "advanced_pins.hpp"
#include "neoled_helper.hpp"
#include "setup.hpp"

AdvancedPins* Setup::pin_setup() {
    
	// Digital
	pinMode(Pin::Digital::UPM, INPUT);
	pinMode(Pin::Digital::USBstart, INPUT);

	pinMode(Pin::Digital::Taste1, INPUT_PULLUP);
	pinMode(Pin::Digital::Taste2, INPUT_PULLUP);
	pinMode(Pin::Digital::Taste3, INPUT_PULLUP);
	pinMode(Pin::Digital::Taste4, INPUT_PULLUP);
	pinMode(Pin::Digital::NotAus, INPUT_PULLUP);
	pinMode(Pin::Digital::OffButton, INPUT_PULLUP);
	
	pinMode(Pin::Digital::VCCrelai, OUTPUT);
	pinMode(Pin::Digital::RecordLED, OUTPUT);

	// Analog
	// Don't need setup using pinMode!

	// PWM
	pinMode(Pin::PWM::RcKanal1, INPUT);
	pinMode(Pin::PWM::RcKanal2, INPUT);
	pinMode(Pin::PWM::RcKanal3, INPUT);

	// Advanced pins - Servos
	AdvancedPins* ap = new AdvancedPins;

	ap->VBox = new Servo;
	ap->VBox->attach(Pin::PWM::VBox);	

	ap->EBox = new Servo;
	ap->EBox->attach(Pin::PWM::EBox);

	// Advanced pins - HX711
	ap->Drehmoment = new Q2HX711(
		Pin::Digital::DrehmomentData, 
		Pin::Digital::DrehmomentClock
	);

	ap->Schub = new Q2HX711(
		Pin::Digital::SchubData,
		Pin::Digital::SchubClock
	);

	// Advanced pins - Neo Pixel LED
	ap->NeoLED = new Adafruit_NeoPixel(
		NeoLED::NumPixels, 
		Pin::Digital::NeoLED, 
		NEO_GRB + NEO_KHZ800
	);

	return ap;
}

void Setup::pin_init(AdvancedPins *ap) {

	/*
	Beim Start des Arduino soll der zweite PNP Transistor sperren
	(das macht er auch ohne HIGH auf diesem Kabel), damit bleibt
	der erste PNP Transistor leitend und das Relais bleibt angezogen
	*/
	digitalWrite(Pin::Digital::VCCrelai, HIGH);
	
	/*
	Beim Starten des Arduino soll der PNP Transistor sperren
	(-> RecordLED leuchtet nicht)
	*/
	digitalWrite(Pin::Digital::RecordLED, HIGH);
	
	ap->VBox->writeMicroseconds(ServoIdle);
	ap->EBox->writeMicroseconds(ServoIdle);
	NeoLED::begin(ap->NeoLED);

}

void Setup::led_startup(Adafruit_NeoPixel* neoLED) {

	// Clear NeoLED pixels, wait 200ms
	NeoLED::clearAll(neoLED);
	delay(200);

	for (int pixel_index = NeoLED::NumPixels; pixel_index > 0; pixel_index++) { 

		// Incrementally increase pixel intensity
		for (int intensity = 0; intensity < 101; intensity++) {
			NeoLED::setColor(
				neoLED,
				pixel_index, 
				intensity, (pixel_index == 0 ? intensity : 0), 0
			); 
			delay(1);
		}

		if (pixel_index == NeoLED::NumPixels) {
			for (int blink_step = 0; blink_step < 20; blink_step++) {
				digitalWrite(Pin::Digital::RecordLED, LOW);
				delay(10);
				digitalWrite(Pin::Digital::RecordLED, HIGH);
				delay(40);
			}

			delay(100);
		}
	}
} 
