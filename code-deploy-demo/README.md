# Simple Demonstration of AWS CodeDeploy.
---
## Preparation 
To run this demo, do the following (tested in us-west-2, adjust for other regions):

1.  Run the "my-codedeploy-demo.template.yml" Cloud Formation template.  
  * It establishes a basic web environment with a few instances running in an AutoScaling group behind a load balancer.  
  * An 'old' version of the app is deployed just to have a starting point, and to keep the load balancer health check from continually rejecting the running EC2 instances.
  * A deployment group is setup which points to the AutoScaling Group

2.  Create a revision:  Open a command prompt inside the /version-1-initial subfolder relative to this readme and run this command:

````
    aws deploy push --application-name MyDemoCodeDeployApplication --s3-location s3://kk-uploads-oregon/CodeDeploy-Example-Revision1.zip
````

...except change the S3 bucket to one of your own buckets.  This creates a new "revision" for version 1 of your app.  If it fails, are you in the correct folder?

3.  Create a second revision: In a separate command prompt within the /version-2-newer subfolder, run this command:

````
    aws deploy push --application-name MyDemoCodeDeployApplication --s3-location s3://kk-uploads-oregon/CodeDeploy-Example-Revision2.zip
````

...adjusting the bucket name as before.  This creates a revision for version 2.

4.  At this point you have uploaded two 'revisions', the old version of the code, and the new version of the code.  

5.  (Optional) On the console under revisions, find the revision 1 zip file, select it, hit deploy, select the existing deployment group.  Under deployment overrides, take "all at once" to make this setup go as fast as possible.  Takes about 5 minutes.  (This establishes an existing deployment that CodeDeploy can roll back to; the software is identical to what was initially deployed, so don't expect to see a difference on the deployed app.)

## Demonstration

1.  Find the Output of the CloudFormation stack.  You will see a URL for the application.  It is running the 'old' version of the software.  Distribute this URL to your students so they can witness the deployment.  Have them note the last 4 digits of the instance ID - it's interesting to watch when specific instances are updated.

2.  Show the revisions:  Go to https://us-west-2.console.aws.amazon.com/codedeploy/home?region=us-west-2#/applications/MyDemoCodeDeployApplication and see the two revisions.  If you did the optional deployment step above, show the deployment.

3.  Under revisions, find the revision 2 zip file, select it, hit deploy, select the existing deployment group.  Under deployment overrides, take one at a time or half at a time, depending on how much demo time you have.  Takes a few minutes for each batch to deploy.  Show the deployment activity, paying attention to which instances are being updated.  Have students compare the instance ids available to those they see on their screens.

4. IF YOU PREVIOUSLY DEPLOYED VERSION 1, you can hit the "Stop and Roll back deployment" button to revert back to the old version.  Demo is most interesting when the deployment is nearly complete when you hit the revert button.  This stops the current deployment and begins a new one.

5.  Delete this stack when done.  Costs around $.03 per hour depending on how many instances you run.
