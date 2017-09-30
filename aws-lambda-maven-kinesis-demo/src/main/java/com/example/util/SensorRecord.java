package com.example.util;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.Charset;
import java.nio.charset.CharsetDecoder;

public class SensorRecord {

	private static CharsetDecoder decoder = Charset.forName("UTF-8").newDecoder();
	private String sensorId;
	private Integer temperature;

	public SensorRecord(String sensorId, Integer temperature) {
		super();
		this.sensorId = sensorId;
		this.temperature = temperature;
	}

	public String getSensorId() {
		return sensorId;
	}

	public void setSensorId(String sensorId) {
		this.sensorId = sensorId;
	}

	public Integer getTemperature() {
		return temperature;
	}

	public void setTemperature(Integer temperature) {
		this.temperature = temperature;
	}

	public static CharsetDecoder getDecoder() {
		return decoder;
	}

	/**
	 * 	Convert a ByteBuffer into a SensorRecord.
	 * 	The ByteBuffer is assumed to be in the 
	 * 	format <sensorId>:<temperature>
	 */
	public static SensorRecord from(ByteBuffer byteBuffer) throws CharacterCodingException {
		String data = decoder.decode(byteBuffer).toString();
		String[] dataParts = data.split(":");
		return new SensorRecord(
			dataParts[0], 
			Integer.parseInt(dataParts[1]));
	}
	
	/**
	 * Convert this SensorRecord into a ByteBuffer.
	 * The ByteBuffer will be in the format <sensorId>:<temperature>
	 */
	public ByteBuffer toByteBuffer() {
	    String data = sensorId + ":" + temperature;
	    return ByteBuffer.wrap(data.getBytes(Charset.forName("UTF-8")));
	}
}
