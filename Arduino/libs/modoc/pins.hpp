#ifndef PINS_H
#define PINS_H

namespace Pin {

	enum Digital {
		UPM =			22,	// 3pol Buchse mit 5V, GND
		DrehmomentData =	33,	// 2pol Buchse + weitere Buchse 5V, GND (HX711)
		DrehmomentClock =	35,	// -"-
		SchubData =		37,	// 2pol Buchse + weitere Buchse 5V, GND (HX711)
		SchubClock =		39,	// -"-
		VCCrelai =		24,	// direktes Kabel
		USBstart =		28,
		Taste1 =		25,	// zusätzlich GND Buchse
		Taste2 =		27,	// -"-
		Taste3 =		29,	// -"-
		Taste4 =		31,	// -"-
		NotAus =		26,	// 2pol Buchse mit GND
		OffButton =		23,
		RecordLED =		30,	// 3pol Buchse + NotAus-Taster + Transitor für LED
		NeoLED =		41,	// Kabel
	};

	enum Analog {
		Temperatur1 =		A0,	// zusätzlich GND Buchse
		Temperatur2 =		A1,	// -"-
		Temperatur3 =		A2,	// -"-
		Temperatur4 =		A3,	// -"-
		Temperatur5 =		A4,	// -"-
		Temperatur6 =		A5,	// -"-
		Temperatur7 =		A6,	// -"-
		Temperatur8 =		A7,	// -"-

		Strom =			A8,
		Spannung =		A9,
		GasPotiVBox =		A10,
		GasPotiEBox =		A11,

		VCCspannung =		A12,
	};

	enum PWM {
		RcKanal1 =		13,	// zusätzlich GND + 5V für Servos von Netzteil
		RcKanal2 =		12,	// -"-
		RcKanal3 =		11,	// -"-
		VBox =			10,	// 3pol Buchse mit 5V, GND
		EBox =			9,	// 3pol Buchse mit 5V, GND
	};
};

#endif
