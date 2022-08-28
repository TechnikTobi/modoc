#ifndef NEOLED_HELPER_H
#define NEOLED_HELPER_H

#include "libs/AdafruitNeoPixel/Adafruit_NeoPixel.h"


namespace NeoLED {

	static const unsigned int NumPixels = 3;

	void begin(Adafruit_NeoPixel *pixels);
	void clear(Adafruit_NeoPixel *pixels, unsigned int index);
	void clearAll(Adafruit_NeoPixel *pixels);
};

#endif
