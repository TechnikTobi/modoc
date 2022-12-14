#ifndef DATA_H
#define DATA_H

#include <Arduino.h>

struct ReadResult {

	long int *data;
	size_t dataSize;
	bool shutdown;

};

static const int UPMcycles = 5;
static const unsigned long UPMtimeoutMicroseconds = 100000;

ReadResult* readData(AdvancedPins *ap, long int sourceVersion);
void readDataGeneral(AdvancedPins *ap, long int *data);
void readDataTemperatur(long int *data);
void readDataControl(long int *data);
void readDataInfo(long int *data, long int sourceVersion);
void readDataString(long int *data);

#endif
