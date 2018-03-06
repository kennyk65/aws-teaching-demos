package com.example.creator;

import com.amazonaws.services.kinesis.AmazonKinesis;
import com.amazonaws.services.kinesis.AmazonKinesisClientBuilder;
import com.amazonaws.services.kinesis.model.DescribeStreamRequest;
import com.amazonaws.services.kinesis.model.ResourceInUseException;
import com.amazonaws.waiters.WaiterParameters;

// The StreamCreator class creates a Kinesis stream
public class StreamCreator {

	// Before running the code, check that
	// the ~/.aws/credentials file has your credentials

	public static final String STREAM_NAME = "KinesisLabStream";
	//public static final Region REGION = Utils.getRegion();
	public static final int WAIT_TIME_MINUTES = 10;
	public static final int POLLING_INTERVAL_SECONDS = 20;
	private static AmazonKinesis kinesis;	//	Use Interface

	
	public static void main(String[] args) throws Exception {
		System.out.println("starting...");
		init();

		// Creates a stream with 2 shards
		createKinesisStream(STREAM_NAME, 2);
	}

	private static void init() throws Exception {

// No longer necessary:		
//		// The ProfileCredentialsProvider will return your default credential
//		// profile by reading from the ~/.aws/credentials file
//		AWSCredentials credentials = null;
//		try {
//			credentials = new ProfileCredentialsProvider().getCredentials();
//		} catch (Exception e) {
//			throw new AmazonClientException(
//					"AmazonClientException represents an error that occurred inside the client on the local host,"
//							+ "either while trying to send the request to AWS or interpret the response." + " "
//							+ "For example, if no network connection is available, the client won't be able to connect to AWS to execute a request and will throw an AmazonClientException.",
//					e);
//		}
		
		//kinesis = new AmazonKinesisClient(credentials).withRegion(REGION);
		
		//	Build a client using the DefaultAWSCredentialsProviderChain (EV's, credential file, etc.)
		//	and using the DefaultAwsRegionProviderChain to get region.
		kinesis = AmazonKinesisClientBuilder.defaultClient();
	}

	private static void createKinesisStream(String streamName, int shardCount) throws Exception {
		try {
			kinesis.createStream(streamName, shardCount);
		} catch (ResourceInUseException re) {
			System.out.printf("Stream %s already exists %n", streamName);
		}

		waitForStreamToBecomeActive(streamName);
	}

	
	//	Clumsy waiter logic:
	private static void waitForStreamToBecomeActive(String streamName) throws Exception {
		
		System.out.printf("Waiting for %s to become ACTIVE... %n", streamName);

		//	Use a Waiter instead of polling:
		kinesis
			.waiters()
				.streamExists()
					.run(
						new WaiterParameters<>(
							new DescribeStreamRequest()
								.withStreamName(STREAM_NAME)));
		
		//	If the above code doesn't blow up, you will reach this:
		System.out.printf("Stream " + streamName + " is ready." );

		
//		String streamStatus = null;
//		boolean isActive = false;
//		long startTime = System.currentTimeMillis();
//		long endTime = startTime + TimeUnit.MINUTES.toMillis(WAIT_TIME_MINUTES);
//
//		while (System.currentTimeMillis() < endTime) {
//			Thread.sleep(TimeUnit.SECONDS.toMillis(POLLING_INTERVAL_SECONDS));
//			streamStatus = getStreamStatus(streamName);
//			System.out.printf("Current stream status: %s%n ", streamStatus);
//			if ("ACTIVE".equals(streamStatus)) {
//				isActive = true;
//				break;
//			}
//		}

//		if (!isActive) {
//			throw new Exception(String.format("Stream %s never became active", streamName));
//		}
	}


//	/**
//	 * Check if Kinesis stream status is active
//	 *
//	 * @param streamName
//	 *            Name of the Kinesis stream
//	 * @return Stream status
//	 */
//	private static String getStreamStatus(String streamName) {
//		return kinesis
//			.describeStream(streamName)
//				.getStreamDescription()
//					.getStreamStatus();
//	}
}
