#ifndef PIN_SETUP_H
#define PIN_SETUP_H

#include "libs/AdafruitNeoPixel/Adafruit_NeoPixel.h"
#include "advanced_pins.hpp"

namespace Setup {

	AdvancedPins* pin_setup();
	void pin_init(AdvancedPins* ap);
	void led_startup(Adafruit_NeoPixel* neoLED);

}

#endif
