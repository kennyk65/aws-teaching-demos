package com.example.consumer;
// Copyright 2017 Amazon Web Services, Inc. or its affiliates. All rights reserved.

import com.amazonaws.services.kinesis.clientlibrary.interfaces.IRecordProcessor;
import com.amazonaws.services.kinesis.clientlibrary.interfaces.IRecordProcessorFactory;

// The SensorRecordProcessorFactory class is used to create new record processors
public class SensorRecordProcessorFactory implements IRecordProcessorFactory {

  public IRecordProcessor createProcessor() {
    return new SensorRecordProcessor();
  }
}
