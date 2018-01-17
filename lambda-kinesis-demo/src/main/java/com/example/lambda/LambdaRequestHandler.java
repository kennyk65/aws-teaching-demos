package com.example.lambda;
import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.KinesisEvent;
import com.amazonaws.services.lambda.runtime.events.KinesisEvent.KinesisEventRecord;
import com.example.consumer.SensorRecordProcessor;
import com.example.consumer.SensorRecordProcessorFactory;

/**
 * Entry point for use as a Lambda function responding to Kinesis Events.
 */
public class LambdaRequestHandler implements RequestHandler<KinesisEvent,String>{
	
	private SensorRecordProcessor processor = 
		(SensorRecordProcessor)
			(new SensorRecordProcessorFactory()).createProcessor();
	
	//	When called from AWS Lambda, The Kinesis event will contain
	//	a collection of records from the associated shard.
	public String handleRequest(KinesisEvent event, Context context) {
		
    	LambdaLogger logger = context.getLogger();
    	int numberOfRecords = event.getRecords()==null?0:event.getRecords().size();
    	logger.log("Start of Function, " + numberOfRecords + " input records");

		
		for ( KinesisEventRecord ker : event.getRecords()) {
			processor.processSingleRecord(ker.getKinesis());
		}

    	logger.log("End of Function, " + 
    			context.getRemainingTimeInMillis() + ", millisecond of time remaining, " +
    			Runtime.getRuntime().freeMemory() + " memory free\n");
    	return "";
	}

	

	  
}
