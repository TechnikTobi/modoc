#include "libs/AdafruitNeoPixel/Adafruit_NeoPixel.cpp"

#include "neoled_helper.hpp"

void NeoLED::begin(Adafruit_NeoPixel *pixels) {
	pixels->begin();
}

void NeoLED::clear(Adafruit_NeoPixel *pixels, unsigned int index) {
	if( !(index < NeoLED::NumPixels)) return;

	pixels->setPixelColor(
		index,
		pixels->Color(0, 0, 0)
	);
	pixels->show();
}

void NeoLED::clearAll(Adafruit_NeoPixel *pixels) {
	for(unsigned int i = 0; i < NeoLED::NumPixels; i++) {
		NeoLED::clear(pixels, i);
	}
}


