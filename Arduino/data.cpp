#include "libs/modoc/fields.hpp"
#include "libs/modoc/pins.hpp"

#include "data.hpp"

ReadResult* readData(long int sourceVersion) {

	// Allocate memory
	long int *data = (long int*)malloc(sizeof(long int) * Field::TotalNum);
	
	// Initialize memory (Q: Is this really necessary?)
	for (size_t i = 0; i < Field::TotalNum; i++) {
		data[i] = 0;
	}

	readDataGeneral(data);
	readDataTemperatur(data);
	readDataControl(data);
	readDataInfo(data, sourceVersion);
	readDataString(data);
	
	ReadResult *result = new ReadResult; 
	result->data = data;
	result->shutdown = (data[Field::Control::OffButton] == LOW);

	return result;
}

void readDataGeneral(long int *data) {

	data[Field::General::UPM] = 0;
	data[Field::General::Drehmoment] = 0;
	data[Field::General::Schub] = 0;
	// RPi: data[Field::General::Ausgangsleistung] = 0;
	data[Field::General::Strom] = 0;
	// RPi: data[Field::General::Eingangsleistung] = 0;
	// RPi: data[Field::General::Wirkungsgrad] = 0;
	data[Field::General::Spritverbrauch] = 0;
	// RPi: data[Field::General::DeltaMax] = 0;
	data[Field::General::GasPotiVBox] = 0;
	data[Field::General::GasPotiEBox] = 0;
	// RPi: data[Field::General::GasProgramm] = 0;
	data[Field::General::Schallpegel] = 0;
	data[Field::General::Vibration] = 0;
	// Deprecated: data[Field::General::RcKanal1] = pulseIn(Pin::PWM::RcKanal1, HIGH, 20000);
	// Deprecated: data[Field::General::RcKanal2] = pulseIn(Pin::PWM::RcKanal2, HIGH, 20000);
	// Deprecated: data[Field::General::RcKanal3] = pulseIn(Pin::PWM::RcKanal3, HIGH, 20000);

}

void readDataTemperatur(long int *data) {

	data[Field::Temperatur::T1] = analogRead(Pin::Analog::Temperatur1); 
	data[Field::Temperatur::T2] = analogRead(Pin::Analog::Temperatur2);
	data[Field::Temperatur::T3] = analogRead(Pin::Analog::Temperatur3);
	data[Field::Temperatur::T4] = analogRead(Pin::Analog::Temperatur4);
	data[Field::Temperatur::T5] = analogRead(Pin::Analog::Temperatur5);
	data[Field::Temperatur::T6] = analogRead(Pin::Analog::Temperatur6);
	data[Field::Temperatur::T7] = analogRead(Pin::Analog::Temperatur7);
	data[Field::Temperatur::T8] = analogRead(Pin::Analog::Temperatur8);
	// Missing: data[Field::Temperatur::TEnv] = 0;
	// Missing: data[Field::Temperatur::FeuchtigkeitEnv] = 0;

}

void readDataControl(long int *data) {

	data[Field::Control::Taste1] = digitalRead(Pin::Digital::Taste1);
	data[Field::Control::Taste2] = digitalRead(Pin::Digital::Taste2);
	data[Field::Control::Taste3] = digitalRead(Pin::Digital::Taste3);
	data[Field::Control::Taste4] = digitalRead(Pin::Digital::Taste4);
	data[Field::Control::NotAus] = digitalRead(Pin::Digital::NotAus);
	data[Field::Control::OffButton] = digitalRead(Pin::Digital::OffButton);

}

void readDataInfo(long int *data, long int sourceVersion) {
	
	data[Field::Info::ArduinoVersion] = sourceVersion;
	data[Field::Info::VCCspannung] = analogRead(Pin::Analog::VCCspannung);
	// RPi: data[Field::Info::Messdauer] = 0;
	// RPi: data[Field::Info::TemperaturCPU] = 0;
	// Missing: data[Field::Info::RTCDate] = 0;
	// Missing: data[Field::Info::RTCTime] = 0;

}

void readDataString(long int *data) {

	// RPi: data[Field::String::Motor] = 0;
	// RPi: data[Field::String::Propeller] = 0;
	// RPi: data[Field::String::Akku] = 0;
	// RPi: data[Field::String::Sprit] = 0;
	// RPi: data[Field::String::Einstellungen] = 0;
	// RPi: data[Field::String::Bemerkungen] = 0;

}
