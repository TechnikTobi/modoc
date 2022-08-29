#ifndef SHUTDOWN_H
#define SHUTDOWN_H

#include "libs/AdafruitNeoPixel/Adafruit_NeoPixel.h"

namespace Shutdown {
	void gracefully(Adafruit_NeoPixel *neoLED);
	void emergency();
}

#endif
