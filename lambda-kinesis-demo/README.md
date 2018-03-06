This project demonstrates a Java-based Lambda function for creating a Kinesis stream, producing 'sensor' records for it, and consuming / analyzing records from it.

More specifically, it is a Maven project that contains all the basic BOM setup for using the AWS Java SDK, Kinesis producer library and client library (which are irritatingly separate from the rest of the Java SDK), and Lambda libraries  (which are ALSO separate from the Java SDK - go figure).

To allow for easy build and upload, the Maven POM uses the 'shade' plugin which copies all dependencies into a single "uber" JAR.

There are three Lambda functions packaged within the JAR:
- com.example.lambda.CreateStreamHandler
- com.example.lambda.SensorReadingsProducerHandler
- com.example.lambda.SensorRecordConsumerHandler

Creator - Creates the KinesisLabStream.  Takes up to 45 seconds and 256M memory.  Role requires basic lambda permissions plus kinesis:CreateStream.

Producer - Generates sample sensor readings with random temperatures.  Needs about 20 seconds and 256M.  Role requires basic lambda permissions plus kinesis:PutRecor*.

Consumer - Reads from the shards and processes the sensor readings, looking for 5 occurrences over a high-temperature threshold.  Takes less than 5 seconds and 256M.  You'll have to triggered this from the Kinesis stream (otherwise, what's the point?).  Role requires basic lambda permissions plus "kinesis:GetRecords", "kinesis:GetShardIterator", "kinesis:DescribeStream", and "kinesis:ListStreams".

The creator, producer, and consumer can be run outside of Lambda of course; Lambda is only used for cool factor.  If running on windows, producer can't use version 0.12 because they dropped support.
