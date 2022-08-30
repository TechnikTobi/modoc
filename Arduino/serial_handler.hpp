#ifndef SERIAL_HANDLER_H
#define SERIAL_HANDLER_H

#include <Arduino.h>

#include "libs/AdafruitNeoPixel/Adafruit_NeoPixel.h"

namespace SerialHandler {

	static const int baudrate = 19200;

	void init();
	void sendData(
		long int *data, 
		size_t dataSize, 
		Adafruit_NeoPixel *neoLED
	);

}

#endif
