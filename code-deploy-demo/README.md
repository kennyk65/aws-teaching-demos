# Simple Demonstration of AWS CodeDeploy.
---
To run this demo, do the following (tested in us-west-2, adjust for other regions):

1.  Run the "my-codedeploy-demo.template.yml" Cloud Formation template.  
  * It establishes a basic web environment with a few instances running in an AutoScaling group behind a load balancer.  
  * An 'old' version of the app is deployed just to have a starting point, and to keep the load balancer health check from continually rejecting the running EC2 instances.
  * A deployment group is setup which points to the AutoScaling Group

2.  Run this command (no way to do this from CloudFormation or Console) FROM THE SAME FOLDER as this readme:

````
    aws deploy push --application-name MyDemoCodeDeployApplication --s3-location s3://kk-uploads-oregon/CodeDeploy-Example-Revision.zip
````

...except change the S3 bucket to one of your own buckets.

3.  Go to https://us-west-2.console.aws.amazon.com/codedeploy/home?region=us-west-2#/applications/MyDemoCodeDeployApplication .  Find the revision that was just uploaded.  Expand it and deploy it to the deployment group.


Note:  The JAR is a new version of the app that we want to deploy.  This happens to be a variant of the spring-cloud-aws-environment-demo.  Could be any Spring Boot JAR web app for this to work.


      
