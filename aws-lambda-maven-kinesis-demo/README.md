This project demonstrates a Java-based Lambda function for consuming records from a Kinesis stream.

More specifically, it is a Maven project that contains all the basic BOM setup for using the AWS Java SDK, Kinesis producer library and client library (which are irritatingly separate from the rest of the Java SDK), and Lambda libraries  (which are ALSO separate from the Java SDK - go figure).

To allow for easy build and upload, the Maven POM uses the 'shade' plugin which copies all dependencies into a single "uber" JAR.

When creating the Lambda function itself, the fully qualified classname of the Lambda handler is com.example.lambda.LambdaRequestHandler.  You'll have to have the Lambda triggered from a Kinesis stream (otherwise, what's the point?).  You will need only basic execution policy/role to run.

This code also contains a "Creator" which creates the stream.  Can be run locally - it isn't part of the Lambda function.

This code also contains a "Producer" which creates data records and puts them on the stream.  This can be run locally - has nothing to do with the lambda function.  If running on windows, can't use version 0.12 because they dropped support.
