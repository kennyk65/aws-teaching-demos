// Copyright 2017 Amazon Web Services, Inc. or its affiliates. All rights reserved.

import static org.junit.Assert.fail;

import java.util.concurrent.TimeUnit;

import org.junit.Test;

import com.amazonaws.AmazonClientException;
import com.amazonaws.AmazonServiceException;
import com.amazonaws.auth.AWSCredentials;
import com.amazonaws.auth.profile.ProfileCredentialsProvider;
import com.amazonaws.regions.Region;
import com.amazonaws.services.kinesis.AmazonKinesisClient;
import com.amazonaws.services.kinesis.model.DescribeStreamRequest;
import com.amazonaws.services.kinesis.model.DescribeStreamResult;
import com.amazonaws.services.kinesis.model.ResourceNotFoundException;

import creator.StreamCreator;

public class StreamCreatedTest {

  @Test
  public void testMain() {

    String streamName = StreamCreator.STREAM_NAME;
    Region region = StreamCreator.REGION;

    String streamStatus = null;
    Exception e = null;
    boolean isActive = false;
    long startTime = System.currentTimeMillis();
    long endTime = startTime + TimeUnit.MINUTES.toMillis(10);

    AWSCredentials credentials = null;
    try {
      StreamCreator.main(new String[0]);
      credentials = new ProfileCredentialsProvider().getCredentials();
    } catch (Exception ex) {
      throw new AmazonClientException(
          "AmazonClientException represents an error that occurred inside the client on the local host,"
              + "either while trying to send the request to AWS or interpret the response."
              + " "
              + "For example, if no network connection is available, the client won't be able to connect to AWS to execute a request and will throw an AmazonClientException.",
          ex);
    }
    AmazonKinesisClient kinesis = new AmazonKinesisClient(credentials);
    kinesis.setRegion(region);

    while (System.currentTimeMillis() < endTime) {
      try {
        Thread.sleep(TimeUnit.SECONDS.toMillis(20));

        DescribeStreamRequest describeStreamRequest = new DescribeStreamRequest();
        describeStreamRequest.setStreamName(streamName);
        DescribeStreamResult describeStreamResponse = kinesis.describeStream(describeStreamRequest);

        streamStatus = describeStreamResponse.getStreamDescription().getStreamStatus();
        if ("ACTIVE".equals(streamStatus)) {
          isActive = true;
          break;
        }
      } catch (ResourceNotFoundException re) {
        e = re;
        break;
      } catch (AmazonServiceException ase) {
        e = ase;
        break;
      } catch (InterruptedException ie) {
        e = ie;
        break;
      }
    }
    if (!isActive) {
      String exMsg = "";
      if (e != null) {
        exMsg = e.toString();
      }
      fail("Kinesis stream was not created or failed to become active. : " + exMsg);
    }
  }
}
