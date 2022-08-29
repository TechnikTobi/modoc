//#include <SPI.h>
//#include <Servo.h>

#include "advanced_pins.hpp"
#include "data.hpp"
#include "neoled_helper.hpp"
#include "serial_handler.hpp"
#include "setup.hpp"
#include "shutdown.hpp"

#define SOURCE_VERSION 100

static AdvancedPins* advancedPins = NULL;

void setup() {

	// Initialize serial connection
	SerialHandler::init();

	// Setup & Initialization of all the pins and their devices
	advancedPins = Setup::pin_setup();
	if (advancedPins == NULL) abort();
	Setup::pin_init(advancedPins);

	// Perform LED startup sequence
	Setup::led_startup(advancedPins->NeoLED);

}

void loop() {

	// Read the data from the pins
	ReadResult* readResult = readData(advancedPins, SOURCE_VERSION);

	// Send the data via the serial connection to the RPi
	SerialHandler::sendData(
		readResult->data,
		readResult->dataSize,
		advancedPins->NeoLED
	);

	// Check for shutdown
	if (readResult->shutdown) Shutdown::gracefully(advancedPins->NeoLED);

	// Don't forget to free the memory!
	free(readResult->data);
	free(readResult);

}
