#ifndef ADVANCED_PINS_H
#define ADVANCED_PINS_H

#include <Servo.h>

#include "libs/HX711/Q2HX711.h"
#include "libs/AdafruitNeoPixel/Adafruit_NeoPixel.h"

static const int ServoIdle = 850;
/*
 850 -> ca. +60°
1500 -> ca.   0°
2200 -> ca. -60°
*/

struct AdvancedPins {

	Servo* VBox;
	Servo* EBox;

	Q2HX711* Drehmoment;
	Q2HX711* Schub;

	Adafruit_NeoPixel* NeoLED;	

};

#endif
