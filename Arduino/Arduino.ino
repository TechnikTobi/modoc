#include <SPI.h>
#include <Servo.h>

#include "libs/modoc/pins.hpp"
#include "libs/modoc/fields.hpp"

#include "advanced_pins.hpp"
#include "data.hpp"
#include "neoled_helper.hpp"
#include "setup.hpp"
#include "shutdown.hpp"

#define SOURCE_VERSION 100

static AdvancedPins* advancedPins = NULL;

void setup() {

  Serial.begin(9600);

  // Setup & Initialization of all the pins and their devices
  advancedPins = Setup::pin_setup();
  if (advancedPins == NULL) abort();

  Setup::pin_init(advancedPins);

  // Perform LED startup sequence
  Setup::led_startup(advancedPins->NeoLED);
  
}

void loop() {

  ReadResult* readResult = readData(SOURCE_VERSION);

  if (readResult->shutdown) Shutdown::gracefully(advancedPins->NeoLED);

  // Don't forget to free the memory!
  free(readResult->data);
  free(readResult);
  
}
