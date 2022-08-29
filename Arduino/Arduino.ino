#include <SPI.h>
#include <Servo.h>

#include "libs/modoc/pins.hpp"

#include "advanced_pins.hpp"
#include "neoled_helper.hpp"
#include "setup.hpp"

void setup() {

  Serial.begin(9600);

  // Setup & Initialization of all the pins and their devices
  AdvancedPins* advancedPins = pin_setup();
  pin_init(advancedPins);

  // Perform LED startup sequence
  led_startup(advancedPins);
  
}

void loop() {

  

}
