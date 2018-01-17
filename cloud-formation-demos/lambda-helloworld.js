
// CloudFormation declaration for this function:
// MyLambda:
//   Type: AWS::Lambda::Function
//   Properties: 
//     FunctionName: MyLambda
//     Description: Example Lambda from CloudFormation
//     MemorySize: 128
//     Timeout: 4
//     Role: !Join [ "", ["arn:aws:iam::", !Ref "AWS::AccountId", ":role/", !Ref LambdaFunctionRole  ] ]  # Would be a lot easier if it didn't have to be in ARN form...
//     Runtime: nodejs6.10
//     Handler: lambda-helloworld.justatest
//     Code:
//	     S3Bucket: kk-uploads-oregon
//       S3Key: lambda-helloworld.js

'use strict';

console.log('Loading function');

exports.justatest = (event, context, callback) => {
  //console.log('Received event:', JSON.stringify(event, null, 2));
  console.log('Hello World!');
  
  // Send response back.  Null means the function was successful. Second parameter tells the API Gateway what to return.
  callback(
  	null, 
	{
		"statusCode": 200,
		"headers": { },
		"body": "Hello World!"
	}
  );   
  //callback('Something went wrong');
};   