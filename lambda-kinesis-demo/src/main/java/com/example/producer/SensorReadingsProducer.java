package com.example.producer;

import com.amazonaws.regions.Region;
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
public class SensorReadingsProducer {

	// 	Before running the code, check that 
	//	the ~/.aws/credentials file has your credentials

	public static final String STREAM_NAME = StreamCreator.STREAM_NAME;
	public static final Region REGION = Utils.getRegion();
	public static final int TOTAL_NUM_EVENTS = 500;
	private static SensorReadingsProducer producer = null;
	private int successCounter = 0;

	
	public static void main(String[] args) {
		producer = new SensorReadingsProducer();
		producer.addDataToStream();
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
			sensorRecord = SensorReadingGenerator.generateData(readingCounter);
			ListenableFuture<UserRecordResult> future = 
				kinesisProducer.addUserRecord(
					STREAM_NAME, 
					sensorRecord.getSensorId(), 
					sensorRecord.toByteBuffer());
			Futures.addCallback(future, myCallback);
		}
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
		config.setVerifyCertificate(false); // Correct unusual error beginning in August of 2018
		return new KinesisProducer(config);
	}


}
