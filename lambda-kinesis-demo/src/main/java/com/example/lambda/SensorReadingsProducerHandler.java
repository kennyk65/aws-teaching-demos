package com.example.lambda;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.example.producer.SensorReadingsProducer;

/**
 * @author kenkrueger
 *
 */
public class SensorReadingsProducerHandler implements RequestHandler<Object, Object> {

	/**
	 * Allow the production of sensor records to be executed via Lambda function.
	 */	
    public Object handleRequest(Object input, Context context) { 

    	LambdaLogger logger = context.getLogger();
    	logger.log("Start of Lambda Function, input: " + input);

    	try {
    		SensorReadingsProducer.main(null);
    	} catch (Exception e) {
    		logger.log(e.getMessage());
    	}
    	
    	logger.log("End of Lambda Function,\n");
    	logger.log( context.getRemainingTimeInMillis() + " millisecond of time remaining.\n");
    	logger.log( Runtime.getRuntime().freeMemory() + " memory free\n");
        return input;
        
    }

}
