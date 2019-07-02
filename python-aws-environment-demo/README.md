# Python / Flask Environment Demo

This is a small, simple web application for displaying EC2 instance metadata.  When running on AWS, it tells you information about the local environment, such as IP addresses, region, zone, etc.
- Demonstrates basic usage of a Flask / Python web app
- Uses ec2-metadata (https://pypi.org/project/ec2-metadata/) to obtain EC2 instance metadata when running in AWS.
- Behaves nicely when running outside of AWS
- Bootstrap is used for formatting.

To run using Elastic Beanstalk:
- (be sure EB CLI is installed)
- From this directory, run (adjust region):
  eb init -p python-3.6 env-demo --region us-west-2
  eb create env-demo

- To update, run eb deploy

