#include <SPI.h>

#include "libs/modoc/pins.hpp"
#include "pin_setup.hpp"

void pin_setup() {
    
    // Digital
    pinMode(Pin::Digital::UPM, INPUT);
    pinMode(Pin::Digital::USBstart, INPUT);
    
    pinMode(Pin::Digital::Taste1, INPUT_PULLUP);
    pinMode(Pin::Digital::Taste2, INPUT_PULLUP);
    pinMode(Pin::Digital::Taste3, INPUT_PULLUP);
    pinMode(Pin::Digital::Taste4, INPUT_PULLUP);
    pinMode(Pin::Digital::NotAus, INPUT_PULLUP);
    pinMode(Pin::Digital::OffButton, INPUT_PULLUP);
    
    // Analog
    // Don't need setup using pinMode!
    
    // PWM
    pinMode(Pin::PWM::RcKanal1, INPUT);
    pinMode(Pin::PWM::RcKanal2, INPUT);
    pinMode(Pin::PWM::RcKanal3, INPUT);
    
}
