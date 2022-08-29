#include <SPI.h>
#include <Servo.h>

#include "advanced_pins.hpp"
#include "setup.hpp"
#include "neoled_helper.hpp"

void setup() {

  Serial.begin(9600);

  // Setup & Initialization of all the pins and their devices
  AdvancedPins* advancedPins = pin_setup();

  // Clear NeoLED pixels, wait 200ms
  NeoLED::clearAll(advancedPins->NeoLED);
  delay(200);
  
}

void loop() {
  // put your main code here, to run repeatedly:

}
