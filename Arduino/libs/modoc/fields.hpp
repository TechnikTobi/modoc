#ifndef FIELDS_H
#define FIELDS_H

namespace Field {

	// Total number of fields to allocate,
	// leaving some empty to expand in the future
	static const size_t TotalNum =	64;

	enum General {			// Indices: 0-19
		UPM =			0,
		Drehmoment =		1,
		Schub =			2,
		Ausgangsleistung =	3,
		Strom =			4,
		Eingangsleistung =	5,
		Wirkungsgrad =		6,
		Spritverbrauch =	7,
		DeltaMax =		8,
		GasPotiVBox =		9,
		GasPotiEBox =		10,
		GasProgramm =		11,
		Schallpegel =		12,
		Vibration =		13,
		RcKanal1 =		14,
		RcKanal2 =		15,
		RcKanal3 =		16,
	};

	enum Temperatur {		// Indices: 20-29
		T1 =			20,
		T2 =			21,
		T3 =			22,
		T4 =			23,
		T5 =			24,
		T6 =			25,
		T7 =			26,
		T8 =			27,
		TEnv =			28,
		FeuchtigkeitEnv =	29,
	};

	enum Control {			// Indices: 30-39
		Taste1 =		30,
		Taste2 =		31,
		Taste3 =		32,
		Taste4 =		33,
		NotAus =		34,
		OffButton =		35,
	};
	
	enum Info {			// Indices: 40-49
		ArduinoVersion =	40,
		VCCspannung =		41,
		Messdauer =		42,
		TemperaturCPU =		43,
		RTCDate =		44,
		RTCTime =		45,
	};

	enum String {			// Indices: 50-59
		Motor =			50,
		Propeller =		51,
		Akku =			52,
		Sprit =			53,
		Einstellungen =		54,
		Bemerkungen =		55

	};
};

#endif
