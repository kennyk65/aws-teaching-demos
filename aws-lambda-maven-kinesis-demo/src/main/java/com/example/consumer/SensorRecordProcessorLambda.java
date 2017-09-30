package com.example.consumer;
import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.KinesisEvent;
import com.amazonaws.services.lambda.runtime.events.KinesisEvent.KinesisEventRecord;

/**
 * Use Lambda as the Kinesis com.example.consumer.
 * 
 * When installed as a Lambda function, this code seeks sensors 
 * which report high temperatures 5 times or more.
 * 
 * WARNING - This code is stateful and will not produce accurate results 
 * between invocations.  Larger batch sizes produce the most accurate results.
 */
public class SensorRecordProcessorLambda implements RequestHandler<KinesisEvent,String>{
	
	private SensorRecordProcessor processor = 
		(SensorRecordProcessor)
			(new SensorRecordProcessorFactory()).createProcessor();
	
	//	When called from AWS Lambda, The Kinesis event will contain
	//	a collection of records from the associated shard.
	public String handleRequest(KinesisEvent event, Context context) {
		for ( KinesisEventRecord ker : event.getRecords()) {
			processor.processSingleRecord(ker.getKinesis());
		}
		return "";
	}

	

	  
}
