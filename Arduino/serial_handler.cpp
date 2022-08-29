#include "libs/modoc/fields.hpp"

#include "neoled_helper.hpp"
#include "serial_handler.hpp"

void SerialHandler::init() {
	Serial.begin(SerialHandler::baudrate);
}

void SerialHandler::sendData(
	long int *data, 
	size_t dataSize, 
	Adafruit_NeoPixel *neoLED
) {

	// First, clear the status LED	
	NeoLED::clear(neoLED, 0);

	if (data[Field::Control::USBstart] == HIGH) {

		// Send the data fields one by one
		for (size_t i = 0; i < dataSize; i++) {
			Serial.print(data[i]);
			Serial.print(";");
		}
	
		// Send end signal
		Serial.print("End");
		Serial.println(";");

		// Let the status LED display green
		NeoLED::setColor(
			neoLED,
			0,
			0, 30, 0
		);

	} else {

		// Wait some time... (for the RPi to come online)
		delay(500);

		// Display yellow to signal the waiting status
		NeoLED::setColor(
			neoLED,
			0,
			100, 100, 0
		);		

	}

}
