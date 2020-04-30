package com.myorg;

import software.amazon.awscdk.core.App;

import java.util.Arrays;

public class BaseNetworkTemplateApp {
    public static void main(final String[] args) {
        App app = new App();

        new BaseNetworkTemplateStack(app, "BaseNetworkTemplateStack");

        app.synth();
    }
}
