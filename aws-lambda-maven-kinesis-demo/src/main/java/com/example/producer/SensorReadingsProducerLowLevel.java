package com.example.producer;

// Copyright 2017 Amazon Web Services, Inc. or its affiliates. All rights reserved.

import java.util.Random;

import com.amazonaws.regions.Region;
import com.amazonaws.services.kinesis.AmazonKinesis;
import com.amazonaws.services.kinesis.AmazonKinesisClientBuilder;
import com.amazonaws.services.kinesis.producer.KinesisProducer;
import com.amazonaws.services.kinesis.producer.KinesisProducerConfiguration;
import com.amazonaws.services.kinesis.producer.UserRecordResult;
import com.example.creator.StreamCreator;
import com.example.util.SensorReadingGenerator;
import com.example.util.SensorRecord;
import com.example.util.Utils;
import com.google.common.util.concurrent.FutureCallback;
import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;

//	The SensorReadingsProducer class 
//	generates data for sensor readings 
//	and publishes records to a Kinesis stream:
public class SensorReadingsProducerLowLevel {

	// 	Before running the code, check that 
	//	the ~/.aws/credentials file has your credentials

	public static final String STREAM_NAME = StreamCreator.STREAM_NAME;
	public static final Region REGION = Utils.getRegion();
	public static final int TOTAL_NUM_EVENTS = 200;
	private static SensorReadingsProducerLowLevel producer = null;
	private int successCounter = 0;

	
	public static void main(String[] args) {
		producer = new SensorReadingsProducerLowLevel();
		producer.addDataToStream();
	}

	private void addDataToStream() {
		SensorRecord sensorRecord = null;
		AmazonKinesis kinesis = AmazonKinesisClientBuilder.defaultClient();

		for (int readingCounter = 0; readingCounter < TOTAL_NUM_EVENTS; readingCounter++) {
			sensorRecord = SensorReadingGenerator.generateData(readingCounter);
			System.out.println("Putting record: " + sensorRecord);
			kinesis.putRecord(
				STREAM_NAME, sensorRecord.toByteBuffer(), sensorRecord.getSensorId());
		}
	}



	public int getSuccessCounter() {
		return successCounter;
	}






}
