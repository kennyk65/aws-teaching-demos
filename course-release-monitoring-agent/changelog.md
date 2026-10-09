
## Change Log ##

1. Alter the default parameter values.  They should be:
BedrockModelId: us.amazon.nova-2-lite-v1:0
NotificationEmail: kenkrueger65@gmail.com
S3BucketName: kk-uploads-oregon
S3ObjectPrefix: aws/course-release-monitor/
ScheduleExpression: cron(0 20 * * ? *) 

2. Fix Lambda permission error, The role is probably too finicky about which model is being used.  Error is:  
  "errorMessage": "An error occurred (AccessDeniedException) when calling the Converse operation: User: arn:aws:sts::011673140073:assumed-role/course-release-monitoring-CourseReleaseMonitorFunct-hTUY2UqfNpEW/course-release-monitoring-agent-monitor is not authorized to perform: bedrock:InvokeModel on resource: arn:aws:bedrock:us-east-2:011673140073:inference-profile/us.amazon.nova-2-lite-v1:0 because no identity-based policy allows the bedrock:InvokeModel action",

3. Adjust Lambda - add an environment variable NOTIFY_CHANGES_ONLY with a default value of true.  When True, there should not be an email sent if no changes are detected from the previous check.  When False, a notification email will be sent on each run, even if it says "no major / minor course changes since xxx".  This will allow me to exercise the email capability, and ensure that the overall process is working.

