#ifndef PIN_SETUP_H
#define PIN_SETUP_H

#include "advanced_pins.hpp"

AdvancedPins* pin_setup();
void pin_init(AdvancedPins* ap);
void led_startup(AdvancedPins* ap);

#endif
