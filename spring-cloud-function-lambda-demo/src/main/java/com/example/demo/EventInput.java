package com.example.demo;



/**
 * This is a model of the Event object sent to the Lambda function by AWS.
 * It can be anything you like, provided it matches the incoming JSON.
 * For example, this one matches the following event input:
 * 
 * {
 *   	"first": "Houie"
 *   	"second": "Dewey"
 *   	"third": "Louis"
 * 	}
 * 
 * 
 */
public class EventInput {

	private String first;
	private String second;
	private String third;
	
	
	public String getFirst() {
		return first;
	}
	public void setFirst(String first) {
		this.first = first;
	}
	public String getSecond() {
		return second;
	}
	public void setSecond(String second) {
		this.second = second;
	}
	public String getThird() {
		return third;
	}
	public void setThird(String third) {
		this.third = third;
	}
	
	
	@Override
	public String toString() {
		return "EventInput [first=" + first + ", second=" + second + ", third=" + third + "]";
	}
	
}
