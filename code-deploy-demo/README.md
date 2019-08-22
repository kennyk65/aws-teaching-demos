# Simple Demonstration of AWS CodeDeploy.
---
To run this demo, do the following (tested in us-west-2, adjust for other regions):

1.  Run the "my-codedeploy-demo.template.yml" Cloud Formation template.  
  * It establishes a basic web environment with a few instances running in an AutoScaling group behind a load balancer.  
  * An 'old' version of the app is deployed just to have a starting point, and to keep the load balancer health check from continually rejecting the running EC2 instances.
  * A deployment group is setup which points to the AutoScaling Group

2.  Find the Output of the CloudFormation stack.  You will see a URL for the application.  It is running the 'old' version of the software.  Distribute this URL to your students so they can witness the deployment.

3.  Open a command prompt in the /version-1-initial subfolder relative to this readme and run this command:

````
    aws deploy push --application-name MyDemoCodeDeployApplication --s3-location s3://kk-uploads-oregon/CodeDeploy-Example-Revision1.zip
````

...except change the S3 bucket to one of your own buckets.  This creates a new "revision" for version 1 of your app.  If it fails, are you in the correct folder?

4.  In a separate command prompt within the /version-2-newer subfolder, run this command:

````
    aws deploy push --application-name MyDemoCodeDeployApplication --s3-location s3://kk-uploads-oregon/CodeDeploy-Example-Revision2.zip
````

...adjusting the bucket name as before.  This creates a revision for version 2.

5.  At this point you have uploaded two 'revisions', the old version of the code, and the new version of the code.  Go to https://us-west-2.console.aws.amazon.com/codedeploy/home?region=us-west-2#/applications/MyDemoCodeDeployApplication and find these revisions.  

6.  Depending on what you want to demo, do one of the following: If you want to demo a simple deployment, skip to step 8.  If you want to demo a rollback scenario, first do step 7 before 8.

7.  (Optional) Under revisions, find the revision 1 zip file, select it, hit deploy, select the existing deployment group, take all the defaults.  Takes about 5 minutes.  Then proceed to step 8. (This establishes an existing revision that CodeDeploy can roll back to; the software is identical to what was initially deployed, so don't expect to see a difference on the screen.)

8.  Under revisions, find the revision 2 zip file, select it, hit deploy, select the existing deployment group, take all the defaults.   Takes about 5 minutes to deploy.  IF YOU PREVIOUSLY DEPLOYED VERSION 1, you can hit the "Stop and Roll back deployment" button to revert back to the old version.  Demo is most interesting when the deployment is nearly complete when you hit the revert button.

9.  Delete this stack when done.  Costs around $.03 per hour depending on how many instances you run.


      
