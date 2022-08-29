#ifndef DATA_H
#define DATA_H

struct ReadResult {

	long int *data;
	bool shutdown;

};

ReadResult* readData(long int sourceVersion);
void readDataGeneral(long int *data);
void readDataTemperatur(long int *data);
void readDataControl(long int *data);
void readDataInfo(long int *data, long int sourceVersion);
void readDataString(long int *data);

#endif
