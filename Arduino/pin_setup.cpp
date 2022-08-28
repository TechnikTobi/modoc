#include <SPI.h>

// Need to include .cpp file for implementation of class functions/constructor/...
#include "libs/HX711/Q2HX711.cpp"

#include "libs/modoc/pins.hpp"

#include "advanced_pins.hpp"
#include "neoled_helper.hpp"
#include "pin_setup.hpp"

AdvancedPins* pin_setup() {
    
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
	digitalWrite(Pin::Digital::VCCrelai, HIGH);
		/*
		Beim Start des Arduino soll der zweite PNP Transistor sperren
		(das macht er auch ohne HIGH auf diesem Kabel), damit bleibt
		der erste PNP Transistor leitend und das Relais bleibt angezogen
		*/

	pinMode(Pin::Digital::RecordLED, OUTPUT);
	digitalWrite(Pin::Digital::RecordLED, HIGH);
		/*
		Beim Starten des Arduino soll der PNP Transistor sperren
		(-> RecordLED leuchtet nicht)
		*/

	

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
	ap->VBox->writeMicroseconds(ServoIdle);

	ap->EBox = new Servo;
	ap->EBox->attach(Pin::PWM::EBox);
	ap->EBox->writeMicroseconds(ServoIdle);

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
	NeoLED::begin(ap->NeoLED);

	return ap;
}
