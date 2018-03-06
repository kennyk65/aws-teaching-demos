package com.example.lambda;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.example.creator.StreamCreator;

/**
 * @author kenkrueger
 *
 */
public class CreateStreamHandler implements RequestHandler<Object, Object> {

	/**
	 * Allow the stream creation to be executed via Lambda function.
	 */	
    public Object handleRequest(Object input, Context context) { 

    	LambdaLogger logger = context.getLogger();
    	logger.log("Start of Lambda Function, input: " + input);

    	try {
    		StreamCreator.main(null);
    	} catch (Exception e) {
    		logger.log(e.getMessage());
    	}
    	
    	logger.log("End of Lambda Function,\n");
    	logger.log( context.getRemainingTimeInMillis() + " millisecond of time remaining.\n");
    	logger.log( Runtime.getRuntime().freeMemory() + " memory free\n");
        return input;
        
    }

}
