package com.example.producer;

// Copyright 2017 Amazon Web Services, Inc. or its affiliates. All rights reserved.

import java.util.Random;

import com.amazonaws.regions.Region;
import com.amazonaws.services.kinesis.producer.KinesisProducer;
import com.amazonaws.services.kinesis.producer.KinesisProducerConfiguration;
import com.amazonaws.services.kinesis.producer.UserRecordResult;
import com.example.creator.StreamCreator;
import com.example.util.SensorRecord;
import com.example.util.Utils;
import com.google.common.util.concurrent.FutureCallback;
import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;

//	The SensorReadingsProducer class 
//	generates data for sensor readings 
//	and publishes records to a Kinesis stream:
public class SensorReadingsProducer {

	// 	Before running the code, check that 
	//	the ~/.aws/credentials file has your credentials

	public static final String STREAM_NAME = StreamCreator.STREAM_NAME;
	public static final Region REGION = Utils.getRegion();
	public static final int TOTAL_NUM_EVENTS = 200;
	private final Random RANDOM = new Random();
	private static SensorReadingsProducer sensorReadingsProducer = null;
	private int successCounter = 0;

	
	public static void main(String[] args) {
		sensorReadingsProducer = getSensorReadingsProducer();
		sensorReadingsProducer.addDataToStream();
	}

	private void addDataToStream() {
		SensorRecord sensorRecord = null;

		KinesisProducer kinesisProducer = createKinesisProducer();

		FutureCallback<UserRecordResult> myCallback = new FutureCallback<UserRecordResult>() {
			@Override
			public void onFailure(Throwable t) {
				System.out.println("Failed to add record to stream.");
				t.printStackTrace();
			};

			@Override
			public void onSuccess(UserRecordResult result) {
				successCounter++;
				if (successCounter == TOTAL_NUM_EVENTS) {
					System.out.println("Number of records added records to stream. :  " + successCounter);
				}
			};
		};

		for (int readingCounter = 0; readingCounter < TOTAL_NUM_EVENTS; readingCounter++) {
			sensorRecord = generateData(readingCounter);
			ListenableFuture<UserRecordResult> future = 
				kinesisProducer.addUserRecord(
					STREAM_NAME, 
					sensorRecord.getSensorId(), 
					sensorRecord.toByteBuffer());
			Futures.addCallback(future, myCallback);
		}
	}

	public static SensorReadingsProducer getSensorReadingsProducer() {
		if (sensorReadingsProducer == null) {
			sensorReadingsProducer = new SensorReadingsProducer();
		}
		return sensorReadingsProducer;
	}

	public int getSuccessCounter() {
		return successCounter;
	}



	/**
	 * Create a KinesisProducer
	 *
	 * @param config
	 *            Kinesis configuration
	 * @return Kinesis com.example.producer
	 */
	private static KinesisProducer createKinesisProducer() {
		KinesisProducerConfiguration config = new KinesisProducerConfiguration();
		config.setRegion(REGION.getName());
		return new KinesisProducer(config);
	}

	// Generates sensor data. DO NOT MODIFY THIS METHOD
	public SensorRecord generateData(int readingCounter) {
		return new SensorRecord(getSensorId(readingCounter), getRandomTemperature(readingCounter));

	}

	private String getSensorId(int readingCounter) {
		String sensorId = null;
		String[] sensorIds = { "A12345", "Z09876" };

		if (readingCounter % 2 == 0) {
			sensorId = sensorIds[0];
		} else {
			sensorId = sensorIds[1];
		}

		return sensorId;
	}

	private int getRandomTemperature(int readingCounter) {
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
