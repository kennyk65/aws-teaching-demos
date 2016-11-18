The AMI Lookup-O-Matic is a facility that allows easy creation of Cloud Formation region lookup mappings.  

Ordinarily, if you have a CloudFormation template defining EC2 instances, and you want it to run in all regions, you have to go through a painstaking process to find the matching AMIs in each region (although automated alternatives are available, see http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/walkthrough-custom-resources-lambda-lookup-amiids.html).  Instead, using this web page, you can simply enter your original AMI and its region, and the page will provide you with a properly formatted CloudFormation mapping table of the matching AMIs in each region.

This tool consists of a HTML page (Bootstrap + Angular) served from any location.  The JS on the page makes a call to a staged resource in my API Gateway, which then calls a Lambda function to produce the mapping table.  A CloudFormation template is provided which builds out the entire system.

This project is mainly a self-education project demonstrating Lambda, API Gateway, and CloudFormation.  As such it is provided for free without any warranty - you should probably double-check the results.
