package com.example;

import java.nio.charset.CharacterCodingException;
import java.nio.charset.Charset;
import java.nio.charset.CharsetDecoder;

import org.junit.Test;

import com.example.util.SensorReadingGenerator;
import com.example.util.SensorRecord;

public class SensorDataTest {

	private static CharsetDecoder decoder = Charset.forName("UTF-8").newDecoder();

	
	@Test
	public void testSensorData() throws CharacterCodingException {
		
		SensorRecord rec = SensorReadingGenerator.generateData(1);
		System.out.println( "Byte buffer <" + decoder.decode(rec.toByteBuffer()) + ">" );
	}
}
