package com.example.producer;

// Copyright 2017 Amazon Web Services, Inc. or its affiliates. All rights reserved.

import java.util.Random;

import com.example.util.SensorRecord;

//	Generates Sensor Readings.:
public class SensorReadingGenerator {

	private static final Random RANDOM = new Random();

	// Generates sensor data. 
	public static SensorRecord generateData(int readingCounter) {
		return new SensorRecord(getSensorId(readingCounter), getRandomTemperature(readingCounter));

	}

	private static String getSensorId(int readingCounter) {
		String sensorId = null;
		String[] sensorIds = { "A12345", "Z09876" };

		if (readingCounter % 2 == 0) {
			sensorId = sensorIds[0];
		} else {
			sensorId = sensorIds[1];
		}

		return sensorId;
	}

	private static int getRandomTemperature(int readingCounter) {
		int temperature = 0;
		int randomNumber = RANDOM.nextInt(10);

		if (readingCounter > 100 && readingCounter < 150 && readingCounter % 2 == 0) {
			temperature = randomNumber + 50;
		} else {
			temperature = randomNumber + 30;
		}
		return temperature;
	}

}
