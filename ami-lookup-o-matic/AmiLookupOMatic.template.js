{
  "AWSTemplateFormatVersion" : "2010-09-09",

  "Description" : "",

  "Parameters" : { },

  "Mappings" : {  },

  "Resources" : { 

    "LambdaFunction": {
      "Type" : "AWS::Lambda::Function",
      "Properties" : {
        "Code" : {
          "S3Bucket": "kk-uploads", 
          "S3Key": "AmiLookupOMatic.js.zip"
        },
        "Description" : "sample",
        "FunctionName" :  "jubjub",
        "Handler" : "index.handler",
        "MemorySize" : 128,
        "Role" : "arn:aws:iam::011673140073:role/service-role/AmiLookupOMaticLambdaRole",
        "Runtime" : "nodejs4.3",
        "Timeout" : 15
    }}

  },

  "Outputs" : {  }
}