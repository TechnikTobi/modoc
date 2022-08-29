#ifndef NEOLED_HELPER_H
#define NEOLED_HELPER_H

#include "libs/AdafruitNeoPixel/Adafruit_NeoPixel.h"


namespace NeoLED {

	static const unsigned int NumPixels = 3;

	void begin(
		Adafruit_NeoPixel *pixels
	);
	void setColor(
		Adafruit_NeoPixel *pixels, 
		unsigned int index, 
		unsigned int red, 
		unsigned int green, 
		unsigned int blue
	);
	void clear(
		Adafruit_NeoPixel *pixels, 
		unsigned int index
	);
	void clearAll(
		Adafruit_NeoPixel *pixels
	);
};

#endif
