package com.myorg;

import java.util.Arrays;

import software.amazon.awscdk.core.CfnParameter;
import software.amazon.awscdk.core.Construct;
import software.amazon.awscdk.core.RemovalPolicy;
import software.amazon.awscdk.core.Stack;
import software.amazon.awscdk.core.StackProps;
import software.amazon.awscdk.services.s3.Bucket;

public class CreateS3BucketStack extends Stack {
    public CreateS3BucketStack(final Construct scope, final String id) {
        this(scope, id, null);

    }

    public CreateS3BucketStack(final Construct scope, final String id, final StackProps props) {
        super(scope, id, props);

        // The code that defines your stack goes here
        CfnParameter bucketName = CfnParameter.Builder.create(this, "bucketName")
        		.description("Globally unique name of your bucket")
        		.defaultValue("kk-temp-test")
        		.build();        
        
        
        Bucket b = Bucket.Builder.create(this, "mybucket")
        		.bucketName(bucketName.getValueAsString())
        		.removalPolicy(RemovalPolicy.DESTROY)
        		.build();
        

    }
}
