#include <SPI.h>
#include <Servo.h>

#include "libs/modoc/pins.hpp"

#include "advanced_pins.hpp"
#include "neoled_helper.hpp"
#include "setup.hpp"

// Allocate memory for the data buffer that holds the different measurements
// Stored as static const so the pointer persists through the entire operation and can't change
static const long int *dataBuffer = (long int*) malloc(sizeof(long int));

void setup() {

  Serial.begin(9600);

  // Setup & Initialization of all the pins and their devices
  AdvancedPins* advancedPins = Setup::pin_setup();
  Setup::pin_init(advancedPins);

  // Perform LED startup sequence
  Setup::led_startup(advancedPins->NeoLED);
  
}

void loop() {

  

}
