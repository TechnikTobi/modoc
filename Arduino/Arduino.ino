#include <SPI.h>
#include <Servo.h>

#include "libs/AdafruitNeoPixel/Adafruit_NeoPixel.h"
#include "libs/HX711/Q2HX711.h"

#include "libs/modoc/pins.hpp"
#include "libs/modoc/fields.hpp"

#include "advanced_pins.hpp"
#include "pin_setup.hpp"

void setup() {
  // put your setup code here, to run once:
  Pin::Digital x = Pin::Digital::Taste1; 
  pin_setup();
}

void loop() {
  // put your main code here, to run repeatedly:

}
