/*
 * The Translator component handles application processing.
 * It is completely independent of the Messaging infrastructure.
 */
package sample;
public class Translator {
    public String translate(String english) {
        String translation = "";
        String [] words = english.split("\\s+");
        for (String word : words)
            translation += translateWord(word) + " ";
        return translation.trim();
    }
    public String translateWord(String word) {
        int length = word.length();
        if (beginsWithConsonant(word)) {
            if (word.matches("^[Qq][Uu].*"))
                return word.substring(2) + word.substring(0, 2) + "ay";
            else {
                word = rotate(word);
                int counter = 1;
                while(!isVowel(word.charAt(0)) && "Yy".indexOf(word.charAt(0)) == -1 && counter < length) {
                    word = rotate(word);
                    counter += 1;
                }
                return word + "ay";
            }
        }
        else
           return word + "way";
    }
    private boolean beginsWithConsonant(String word) {
    		return !isVowel(word.charAt(0));
    }
    private boolean isVowel(char letter) {
    		return "AEIOUaeiou".indexOf(letter) != -1;
    }
    private String rotate(String word) {
    		return word.substring(1) + word.charAt(0);
    }
}
