#include <SPI.h>

// Need to include .cpp files for implementation of class functions/constructor/...
#include "libs/HX711/Q2HX711.cpp"
#include "libs/AdafruitNeoPixel/Adafruit_NeoPixel.cpp"

#include "libs/modoc/pins.hpp"

#include "advanced_pins.hpp"
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
		NeoLEDnumPixels, 
		Pin::Digital::NeoLED, 
		NEO_GRB + NEO_KHZ800
	);

	return ap;
}
