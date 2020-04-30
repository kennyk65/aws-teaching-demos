package com.myorg;

import software.amazon.awscdk.core.App;

import java.util.Arrays;

public class CreateS3BucketApp {
    public static void main(final String[] args) {
        App app = new App();

        new CreateS3BucketStack(app, "CreateS3BucketStack");

        app.synth();
    }
}
