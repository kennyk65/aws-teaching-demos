package com.example.lambda;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;
import com.amazonaws.services.lambda.runtime.RequestHandler;

public class LambdaFunctionHandler implements RequestHandler<Object, Object> {

    public Object handleRequest(Object input, Context context) { 

    	LambdaLogger logger = context.getLogger();
    	logger.log("Start of Lambda Function, input: " + input);

    	logger.log("End of Lambda Function,\n");
    	logger.log( context.getRemainingTimeInMillis() + " millisecond of time remaining.\n");
    	logger.log( Runtime.getRuntime().freeMemory() + " memory free\n");
        return input;
        
    }

}
