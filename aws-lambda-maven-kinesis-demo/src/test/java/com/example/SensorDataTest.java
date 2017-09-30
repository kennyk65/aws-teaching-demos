package com.example;

import java.nio.charset.CharacterCodingException;
import java.nio.charset.Charset;
import java.nio.charset.CharsetDecoder;

import org.junit.Test;

import com.example.producer.SensorReadingsProducer;
import com.example.util.SensorRecord;

public class SensorDataTest {

	private static CharsetDecoder decoder = Charset.forName("UTF-8").newDecoder();

	SensorReadingsProducer producer = new SensorReadingsProducer();
	
	@Test
	public void testSensorData() throws CharacterCodingException {
		
		SensorRecord rec = producer.generateData(1);
		System.out.println( "Byte buffer <" + decoder.decode(rec.toByteBuffer()) + ">" );
	}
}
