package consumer;
// Copyright 2017 Amazon Web Services, Inc. or its affiliates. All rights reserved.

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.UUID;

import com.amazonaws.AmazonClientException;
import com.amazonaws.auth.AWSCredentials;
import com.amazonaws.auth.AWSCredentialsProvider;
import com.amazonaws.auth.profile.ProfileCredentialsProvider;
import com.amazonaws.regions.Region;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDBClient;
import com.amazonaws.services.kinesis.AmazonKinesisClient;
import com.amazonaws.services.kinesis.clientlibrary.lib.worker.InitialPositionInStream;
import com.amazonaws.services.kinesis.clientlibrary.lib.worker.KinesisClientLibConfiguration;
import com.amazonaws.services.kinesis.clientlibrary.lib.worker.Worker;
import com.amazonaws.services.kinesis.model.ResourceNotFoundException;

import creator.StreamCreator;
import util.Utils;

// The SensorAlertApplication class processes sensor records and raises an alert if the temperature is above a threshold
public final class SensorAlertApplication {

  // Before running the code, check that the ~/.aws/credentials file contains your credentials

  public static final Region REGION = Utils.getRegion();

  // Name of the Kinesis stream on which the sensor data will be uploaded/downloaded
  public static final String STREAM_NAME = StreamCreator.STREAM_NAME;
  
  // Name of current application
  private static final String APPLICATION_NAME = "SensorAlertApplication";

  // Initial position in the stream when the application starts up for the first time.
  // Position can be one of LATEST (most recent data) or TRIM_HORIZON (oldest available data)
  private static final InitialPositionInStream APPLICATION_INITIAL_POSITION_IN_STREAM =
      InitialPositionInStream.LATEST;

  private static AWSCredentialsProvider credentialsProvider;
  private static String highTempSensorId = null;

  
  private static void init() {
    // Ensure the JVM will refresh the cached IP values of AWS resources (e.g. service endpoints)
    java.security.Security.setProperty("networkaddress.cache.ttl", "60");

    // The ProfileCredentialsProvider will return your default credential profile 
    // by reading from the ~/.aws/credentials file
    credentialsProvider = new ProfileCredentialsProvider();
    try {
      credentialsProvider.getCredentials();
    } catch (Exception e) {
      throw new AmazonClientException(
          "AmazonClientException represents an error that occurred inside the client on the local host,"
              + "either while trying to send the request to AWS or interpret the response."
              + " "
              + "For example, if no network connection is available, the client won't be able to connect to AWS to execute a request and will throw an AmazonClientException.",
          e);
    }
  }

  
  public static void main(String[] args) throws Exception {
    init();
    if (args.length == 1 && "delete-resources".equals(args[0])) {
      deleteResources();
      return;
    }
    processSensorData();
  }

  
  private static void processSensorData() throws UnknownHostException {
	
	// Make a unique worker ID to distinguish this instance from any others running elsewhere:
	String workerId = InetAddress.getLocalHost().getCanonicalHostName() + ":" + UUID.randomUUID();
	  
	  //	 Create a Configuration and worker.  The Worker requires a SensorRecordProcessorFactory:
    KinesisClientLibConfiguration kinesisClientLibConfiguration = createKinesisConfig(workerId);
    Worker worker = createWorker(kinesisClientLibConfiguration);

    System.out.printf("Running %s to process stream %s as worker %s...", APPLICATION_NAME, STREAM_NAME, workerId);
    int exitCode = 0;

    //	Run the worker:
    try {
      worker.run();
    } catch (Throwable t) {
      System.err.println("Caught throwable while processing record");
      t.printStackTrace();
      exitCode = 1;
    }
    System.exit(exitCode);
  }

  
  public static void deleteResources() {
    AWSCredentials credentials = credentialsProvider.getCredentials();

    // Delete the stream
    AmazonKinesisClient kinesis = new AmazonKinesisClient(credentials);
    kinesis.setRegion(REGION);

    System.out.printf("Deleting the stream", STREAM_NAME);
    try {
      kinesis.deleteStream(STREAM_NAME);
    } catch (ResourceNotFoundException ex) {
      // The stream doesn't exist
      ex.printStackTrace();
    }

    AmazonDynamoDBClient dynamoDB = new AmazonDynamoDBClient(credentialsProvider.getCredentials());
    dynamoDB.setRegion(REGION);

    System.out.printf("Deleting the table", APPLICATION_NAME);
    try {
      dynamoDB.deleteTable(APPLICATION_NAME);
    } catch (com.amazonaws.services.dynamodbv2.model.ResourceNotFoundException ex) {
      ex.printStackTrace();
    }
  }

  public static void setSensorHighTemperatureAlert(String sensorId) {
    highTempSensorId = sensorId;
  }

  public static String getSensorHighTemperatureAlert() {
    return highTempSensorId;
  }

  /**
   * Create an instance of KinesisClientLibConfiguration initialize stream position and initialize
   * region
   *
   * @param workerId    Worker ID
   * @return            Kinesis config
   */
  private static KinesisClientLibConfiguration createKinesisConfig(String workerId) {
    // STUDENT TODO 7: Replace the solution with your own code
//    return Solution.createKinesisConfig(
//        APPLICATION_NAME,
//        STREAM_NAME,
//        credentialsProvider,
//        workerId,
//        APPLICATION_INITIAL_POSITION_IN_STREAM,
//        REGION);
  		return
  			new KinesisClientLibConfiguration(
  				APPLICATION_NAME, STREAM_NAME, credentialsProvider, workerId)
  			.withInitialPositionInStream(APPLICATION_INITIAL_POSITION_IN_STREAM)
  			.withRegionName(REGION.getName())
		;
  }

  /**
   * Create an instance of SensorRecordProcessorFactory and use that to create an instance of Worker
   *
   * @param config    Kinesis client library configuration
   * @return          Worker instance
   */
  private static Worker createWorker(KinesisClientLibConfiguration config) {
    // STUDENT TODO 8: Replace the solution with your own code
//    return Solution.createWorker(config);
	  return new Worker(new SensorRecordProcessorFactory(), config);
  }
}
