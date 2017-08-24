package consumer;
// Copyright 2017 Amazon Web Services, Inc. or its affiliates. All rights reserved.

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.util.HashMap;
import java.util.List;

import com.amazonaws.services.kinesis.clientlibrary.exceptions.InvalidStateException;
import com.amazonaws.services.kinesis.clientlibrary.exceptions.ShutdownException;
import com.amazonaws.services.kinesis.clientlibrary.exceptions.ThrottlingException;
import com.amazonaws.services.kinesis.clientlibrary.interfaces.IRecordProcessor;
import com.amazonaws.services.kinesis.clientlibrary.interfaces.IRecordProcessorCheckpointer;
import com.amazonaws.services.kinesis.clientlibrary.types.ShutdownReason;
import com.amazonaws.services.kinesis.model.Record;

import util.SensorRecord;

// The SensorRecordProcessor class processes records and checkpoints progress
public class SensorRecordProcessor implements IRecordProcessor {

	private String kinesisShardId;

	// Backoff and retry settings
	private static final long BACKOFF_TIME_IN_MILLIS = 3000L;
	private static final int NUM_RETRIES = 10;

	// Checkpoint about once a minute
	private static final long CHECKPOINT_INTERVAL_MILLIS = 60000L;
	private long nextCheckpointTimeInMillis;

	private static final int TEMPERATURE_THRESHOLD = 50;
	private static final int ALERT_AFTER_NUM_HIGHS = 5;

	// WARNING! STATEFUL CODE!
	HashMap<String, Integer> sensorHighs = new HashMap<>();

	@Override
	public void initialize(String shardId) {
		System.out.println("Initializing record processor for shard: " + shardId);
		kinesisShardId = shardId;
	}

	@Override
	public void processRecords(List<Record> records, IRecordProcessorCheckpointer checkpointer) {

		System.out.println("Processing " + records.size() + " records from " + kinesisShardId);

		// Process records and perform all exception handling
		processRecordsWithRetries(records);

		// Checkpoint once every checkpoint interval
		if (System.currentTimeMillis() > nextCheckpointTimeInMillis) {
			checkpoint(checkpointer);
			nextCheckpointTimeInMillis = System.currentTimeMillis() + CHECKPOINT_INTERVAL_MILLIS;
		}
	}

	/**
	 * Process records performing retries as needed. Skip "poison pill" records.
	 *
	 * @param Data
	 *            records to be processed.
	 */
	private void processRecordsWithRetries(List<Record> records) {
		for (Record record : records) {
			boolean processedSuccessfully = false;
			for (int i = 0; i < NUM_RETRIES; i++) {
				try {
					processSingleRecord(record);
					processedSuccessfully = true;
					break;
				} catch (Throwable t) {
					System.out.println("Caught throwable while processing record " + record + " : " + t);
				}

				// Back off if we encounter an exception
				backoff();
			}

			if (!processedSuccessfully) {
				System.out.println("Couldn't process record " + record + " Skipping the record. ");
			}
		}
	}

	/**
	 * Process a single record.
	 *
	 * @param record
	 *            The record to be processed
	 */
	public void processSingleRecord(Record record) {

		int highTempCounterForSensor = 0;

		try {

			// Get the data blob from the Kinesis record
			// and turn it into a SensorRecord:
			SensorRecord rec = SensorRecord.from(record.getData());

			System.out.printf("Processing single record sensor id: %s, temperature: %d. %n", rec.getSensorId(),
					rec.getTemperature());

			// If the temperature is above the threshold...
			if (rec.getTemperature() > TEMPERATURE_THRESHOLD) {

				// Retrieve previous high temperature counter for this sensor
				// from sensorHighs HashMap
				if (sensorHighs.containsKey(rec.getSensorId())) {
					highTempCounterForSensor = sensorHighs.get(rec.getSensorId());
				}

				// Update this counter if the current temperature reading is
				// higher than threshold
				highTempCounterForSensor++;
				sensorHighs.put(rec.getSensorId(), highTempCounterForSensor);

				// Update alert variables in SensorApplication if temperature
				// exceeds threshold multiple times
				if (highTempCounterForSensor > ALERT_AFTER_NUM_HIGHS) {
					System.out.println("HIGH TEMPERATURE ALERT!!! sensor id " + rec.getSensorId());
					SensorAlertApplication.setSensorHighTemperatureAlert(rec.getSensorId());
				}
			}

		} catch (NumberFormatException e) {
			System.out.println(
					"Record does not match application record format. Ignoring record with data; " + record.getData());
		} catch (CharacterCodingException e) {
			System.out.println("Malformed data: " + record.getData() + " : " + e);
		}
	}

	@Override
	public void shutdown(IRecordProcessorCheckpointer checkpointer, ShutdownReason reason) {
		System.out.println("Shutting down record processor for shard: " + kinesisShardId);
		// Important to checkpoint after reaching end of shard, so we can start
		// processing data from child shards
		if (reason == ShutdownReason.TERMINATE) {
			checkpoint(checkpointer);
		}
	}

	/**
	 * Checkpoint with retries
	 *
	 * @param checkpointer
	 */
	private void checkpoint(IRecordProcessorCheckpointer checkpointer) {
		System.out.println("Checkpointing shard " + kinesisShardId);
		for (int attempts = 0; attempts < NUM_RETRIES; attempts++) {
			try {
				checkpointer.checkpoint();
				break;
			} catch (ThrottlingException e) {
				// Backoff and re-attempt checkpoint upon transient failures
				backoff();
			} catch (ShutdownException | InvalidStateException e) {
				System.out.println("Caught exception, skipping checkpoint. : " + e);
				// ShutdownException: Ignore checkpoint if the processor
				// instance has been shutdown (fail over).
				// InvalidStateException: This indicates an issue with the
				// DynamoDB table used by the Amazon Kinesis Client Library
				// (check table, provisioned IOPS).
				break;
			}
		}
	}

	private void backoff() {
		try {
			Thread.sleep(BACKOFF_TIME_IN_MILLIS);
		} catch (InterruptedException e) {
			System.out.println("Interrupted sleep : " + e);
		}
	}

	/**
	 * Retrieve data from record
	 *
	 * @param record
	 *            Name of the Kinesis stream
	 * @return Record to be processed
	 */
	private ByteBuffer getRecordData(Record record) {
		// STUDENT TODO 9: Replace the solution with your own code
		// return Solution.getRecordData(record);
		return record.getData();

	}
}
