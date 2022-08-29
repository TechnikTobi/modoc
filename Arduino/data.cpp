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

	// Calculation of UPM ("Umdrehungen pro Minute")
	// Take multiple samples to average out fluctuations
	unsigned long UPMvalue = 0;
	for (int i = 0; i < UPMcycles; i++) {
		unsigned long UPMpulse = pulseIn(Pin::Digital::UPM, HIGH, UPMtimeoutMicroseconds);
		if (UPMpulse == 0) break;
		UPMvalue += UPMpulse;
	}
	UPMvalue /= UPMcycles;

	data[Field::General::UPM] = UPMvalue;
	data[Field::General::Drehmoment] = 0;
	data[Field::General::Schub] = 0;
	data[Field::General::Spannung] = analogRead(Pin::Analog::Spannung);
	data[Field::General::Strom] = analogRead(Pin::Analog::Strom);
	data[Field::General::GasPotiVBox] = analogRead(Pin::Analog::GasPotiVBox);
	data[Field::General::GasPotiEBox] = analogRead(Pin::Analog::GasPotiEBox);
	// RPi: data[Field::General::Ausgangsleistung] = 0;
	// RPi: data[Field::General::Eingangsleistung] = 0;
	// RPi: data[Field::General::Wirkungsgrad] = 0;
	// RPi: data[Field::General::DeltaMax] = 0;
	// RPi: data[Field::General::GasProgramm] = 0;
	// Missing: data[Field::General::Spritverbrauch] = 0;
	// Missing: data[Field::General::Schallpegel] = 0;
	// Missing: data[Field::General::Vibration] = 0;
	// Note: RcKanal1-3 deprecated as of 2020-02-23: Entfernt für höhere Samplingrate
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
