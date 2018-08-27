#!/usr/bin/env python
# -*- coding: utf-8 -*-

import boto3
import cfnresponse

def lambda_handler(event, context):

    if event['RequestType'] == 'Delete':
        s3 = boto3.resource('s3')
        bucket = s3.Bucket('test-remove-bucket')
        for obj in bucket.objects.filter():
            s3.Object(bucket.name, obj.key).delete()

    cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, "CustomResourcePhysicalID")
After you create the lambda above, just put the CustomResource in your CloudFormation stack:

"removeBucket": {
        "Type": "Custom::customlambda",
        "Properties": {
          "ServiceToken": "arn:aws:lambda:eu-west-1:123456789000:function:custom-lambda-name",
        }
}