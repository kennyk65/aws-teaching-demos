package sample;

import java.io.InputStream;

import com.amazonaws.services.polly.AmazonPolly;
import com.amazonaws.services.polly.AmazonPollyClientBuilder;
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

public class Speaker {

	//	Create Polly resource using the credentials and region described in ~/.aws/ folder:
	private static final AmazonPolly polly = AmazonPollyClientBuilder.defaultClient();
	
	
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
	
	public static void speak(final String sentence, int rate, int pause) throws Exception {
		speak(toSsml(sentence,rate,pause));
	}
		
	public static void speak(final String sentence) throws Exception {
		
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
	
}
