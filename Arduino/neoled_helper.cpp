#include "libs/AdafruitNeoPixel/Adafruit_NeoPixel.cpp"

#include "neoled_helper.hpp"

void NeoLED::begin(
	Adafruit_NeoPixel *pixels
) {
	pixels->begin();
}

void NeoLED::setColor(
	Adafruit_NeoPixel *pixels, 
	unsigned int index, 
	unsigned int red, 
	unsigned int green, 
	unsigned int blue
) {
	pixels->setPixelColor(
		index,
		pixels->Color(green, red, blue)
	);
	/*
		Due to the behaviour of the MoDoc hardware the channels
		for red and green are swapped (see previous software
		versions)
	*/
	pixels->show();
}

void NeoLED::clear(
	Adafruit_NeoPixel *pixels, 
	unsigned int index
) {
	if( !(index < NeoLED::NumPixels)) return;
	NeoLED::setColor(pixels, index, 0, 0, 0);
}

void NeoLED::clearAll(
	Adafruit_NeoPixel *pixels
) {
	for(unsigned int i = 0; i < NeoLED::NumPixels; i++) {
		NeoLED::clear(pixels, i);
	}
}

