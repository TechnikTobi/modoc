#ifndef FIELDS_H
#define FIELDS_H

namespace Field {

    enum Index {

        // Allgemein: 0-19
        UPM =					0,
        Drehmoment =			1,
        Schub =					2,
        Ausgangsleistung =		3,
        Strom =					4,
        Eingangsleistung =		5,
        Wirkungsgrad =			6,
        Spritverbrauch =		7,
        DeltaMax =				8,
        GasPotiVBox =			9,
        GasPotiEBox =			10,
        GasProgramm =			11,
        Schallpegel =			12,
        Vibration =				13,
        RcKanal1 =				14,
        RcKanal2 =				15,
        RcKanal3 =				16,

        // Temperatur & Umgebung: 20-29
        Temperatur1 =			20,
        Temperatur2 =			21,
        Temperatur3 =			22,
        Temperatur4 =			23,
        Temperatur5 =			24,
        Temperatur6 =			25,
        Temperatur7 =			26,
        Temperatur8 =			27,
        TemperaturEnv =			28,
        FeuchtigkeitEnv =		29,

        // MoDoc Controls: 30-39
        Taste1 =				30,
        Taste2 =				31,
        Taste3 =				32,
        Taste4 =				33,
        NotAus =				34,
        OffButton =				35,

        // Info (Arduino & Raspberry): 40-49
        ArduinoVersion =		40,
        Messdauer =				41,
        VCCspannung =			42,
        TemperaturCPU =			43,
        RTCDate =				44,
        RTCTime =				45,

        // Strings: 50-59
        Motor =					50,
        Propeller =				51,
        Akku =					52,
        Sprit =					53,
        Einstellungen =			54,
        Bemerkungen =			55

    };
};

#endif
