package sample;

import java.io.InputStream;
import java.util.Scanner;

import com.amazonaws.ClientConfiguration;
import com.amazonaws.auth.DefaultAWSCredentialsProviderChain;
import com.amazonaws.regions.Region;
import com.amazonaws.regions.Regions;
import com.amazonaws.services.polly.AmazonPollyClient;
import com.amazonaws.services.polly.model.DescribeVoicesRequest;
import com.amazonaws.services.polly.model.DescribeVoicesResult;
import com.amazonaws.services.polly.model.OutputFormat;
import com.amazonaws.services.polly.model.SynthesizeSpeechRequest;
import com.amazonaws.services.polly.model.SynthesizeSpeechResult;
import com.amazonaws.services.polly.model.TextType;
import com.amazonaws.services.polly.model.Voice;

import javazoom.jl.player.advanced.AdvancedPlayer;
import javazoom.jl.player.advanced.PlaybackEvent;
import javazoom.jl.player.advanced.PlaybackListener;

public class Main {
	
	public static void main(String [] args) throws Exception {
		
		final Translator translator = new Translator();
		String english = "";
		String pigLatin = "";
		
		// Inspect the command line argument for input.
		if (args.length != 0 ) {
			for (String word : args)
				english += word + " ";
		}
		else
			english = getSentence();
		
		// Strip whitespace from the edges.
		english = english.trim();
		
		// If anything remains, translate it.
		if (!english.equals(""))
			pigLatin = translator.translate(english);
		
		// Display the translation
		System.out.println("English		: " + english);
		System.out.println("Pig Latin	: " + pigLatin);

		// Control the rate of speech, and the delay between words.
		final String englishSsml = toSsml("The Pig Latin Translation Of " + english + " Is", 95, 0);
		// The Pig Latin vocalization leaves something to be desired.
		// I could use phonemes, but that's a topic for another time.
		final String pigLatinSsml = toSsml(pigLatin, 95, 10);
		
		// Respond verbally.
		speak(englishSsml);
		speak(pigLatinSsml);
	}
	
	public static final String toSsml(String sentence, int rate, int pause) {
		final String [] words = sentence.split("\\s+");
		String ssml = "<speak><prosody";
		// This controls the rate of speech as a % of the normal rate.
		if (rate > 0)
			ssml += " rate='" + rate + "%'";
		ssml += ">";
		for (int count = 0, last = words.length - 1; count <= last; count++) {
			ssml += words[count] + " ";
			if (count < last) {
				// This controls the delay between words measured in milliseconds.
				if (pause > 0)
					ssml += "<break time='" + pause + "ms'/>";
			}
		}
		ssml += "</prosody></speak>";
		return ssml;
	}
	
	public static void speak(final String sentence) throws Exception {
		// Define the polly client for a particular region.
		final Region region = Region.getRegion(Regions.US_WEST_1);
		final AmazonPollyClient polly = new AmazonPollyClient(new DefaultAWSCredentialsProviderChain(), new ClientConfiguration());
		polly.setRegion(region);
		
		// Create a describe voices request.
		DescribeVoicesRequest describeVoicesRequest = new DescribeVoicesRequest();

		// Ask Amazon Polly to describe available TTS voices.
		DescribeVoicesResult describeVoicesResult = polly.describeVoices(describeVoicesRequest);
/*
English voices
35: {Gender: Female,Id: Salli,LanguageCode: en-US,LanguageName: US English,Name: Salli}
36: {Gender: Male,Id: Matthew,LanguageCode: en-US,LanguageName: US English,Name: Matthew}
37: {Gender: Female,Id: Kimberly,LanguageCode: en-US,LanguageName: US English,Name: Kimberly}
38: {Gender: Female,Id: Kendra,LanguageCode: en-US,LanguageName: US English,Name: Kendra}
39: {Gender: Male,Id: Justin,LanguageCode: en-US,LanguageName: US English,Name: Justin}
40: {Gender: Male,Id: Joey,LanguageCode: en-US,LanguageName: US English,Name: Joey}
41: {Gender: Female,Id: Joanna,LanguageCode: en-US,LanguageName: US English,Name: Joanna}
42: {Gender: Female,Id: Ivy,LanguageCode: en-US,LanguageName: US English,Name: Ivy}
 */
		// Select a voice.
		final int voiceID = 40;
		final Voice voice = describeVoicesResult.getVoices().get(voiceID);		
		final SynthesizeSpeechRequest synthReq = new SynthesizeSpeechRequest().withTextType(TextType.Ssml).withText(sentence).withVoiceId(voice.getId()).withOutputFormat(OutputFormat.Mp3);
		final SynthesizeSpeechResult synthRes = polly.synthesizeSpeech(synthReq);
		final InputStream speechStream = synthRes.getAudioStream();
		
		// Create an MP3 player
		AdvancedPlayer player = new AdvancedPlayer(speechStream, javazoom.jl.player.FactoryRegistry.systemRegistry().createAudioDevice());

		player.setPlayBackListener(new PlaybackListener() {
			@Override
			public void playbackStarted(PlaybackEvent evt) {}
			@Override
			public void playbackFinished(PlaybackEvent evt) {}
		});		
		
		// Play it!
		player.play();
	}
	
	public static String getSentence() {
		System.out.println("Welcome to the english to pig latin translator");
		System.out.println("Enter a word or phrase in english and I will tell you how to say it in pig latin");
		System.out.print("Input : ");
		
		Scanner scanner = new Scanner(System.in);
		String sentence = scanner.nextLine();
		scanner.close();
		return sentence;
	}
} 
