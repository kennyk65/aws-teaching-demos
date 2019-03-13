package sample;

import java.util.Scanner;

public class Main {
	
	public static void main(String [] args) throws Exception {
		
		final Translator translator = new Translator();
		String english = "";
		String pigLatin = "";
		
		// Inspect the command line argument for input.
		if (args.length != 0 ) {
			for (String word : args)
				english += word + " ";
		} else {
			// Otherwise, prompt for a sentence:
			english = getSentenceFromStdIn();
		}
			
		// Strip whitespace from the edges.
		english = english.trim();
		
		// If anything remains, translate it.
		if (!english.equals(""))
			pigLatin = translator.translate(english);
		
		// Display the translation
		System.out.println("English		: " + english);
		System.out.println("Pig Latin	: " + pigLatin);

		// Control the rate of speech, and the delay between words.
		// The Pig Latin vocalization leaves something to be desired.
		// I could use phonemes, but that's a topic for another time.
		Speaker.speak("The Pig Latin Translation Of " + english + " Is", 95, 0);
		Speaker.speak(pigLatin, 95, 10);
	}
	

	
	public static String getSentenceFromStdIn() {
		System.out.println("Welcome to the english to pig latin translator");
		System.out.println("Enter a word or phrase in english and I will tell you how to say it in pig latin");
		System.out.print("Input : ");
		
		Scanner scanner = new Scanner(System.in);
		String sentence = scanner.nextLine();
		scanner.close();
		return sentence;
	}
} 
