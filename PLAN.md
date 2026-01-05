# Chinese Tutor

This is a plan for an intelligent tutoring system for a student of Chinese
language. Assume that the student is following the HSK curriculum. The goal of
the system is to produce exercises that tests the student's current abilities,
gather feedback from the exercise results, and tailor future exercise in light
of that feedback.

- For now, the interface of the program is standard input/output.

- The system will use Bayesian Knowledge Tracing (BKT), which uses a hidden
  Markov model to track student's current expertise.

- The system will contain a repository of knowledge points, which includes both
  grammar and vocabulary. The system should track the student's mastery of each
  knowledge point.

- The system should also track and test the student's misconceptions. Along with
  knowledge points, there should also be a repository of common misconceptions,
  particularly for students who are English speakers (e.g. placing time phrases
  at the end of a sentence).

- Exercises should be tagged with a difficulty level, so that appropriately
  difficult exercises are provided to the student. The difficulty level can be
  computed by the type of exercise, whether it also tests student
  misconceptions, etc.

- The system should appropriately schedule exercises for the student to meet the following goals:
    - test student's existing expertise
    - test student's misconceptions
    - expand student's "knowledge frontier" 

## Exercise Types

The following are example of exercise types the system shows to the student. It is NOT exhaustive.

* Segmented Translation: Provide a sentence in English and several Chinese "chunks." The student must select the chunks in the right order.

* Fill in the Correct Blank: Given a character/phrase, pick the right blank to put the character in

* Grammar Transformation: Give a statement and ask the student to turn it into a question, or a negative sentence, or change tense, etc.
	* Example: "他是学生。" → Change to negative using pinyin input → 他不是学生.

* The "Minimal Pair" Distractor: A multiple-choice question where the options are visually similar characters, or characters that sound similar.
	* Example: Select the character for "to buy" (mǎi). Options: `A. 买 (Correct)  B. 卖 (To sell)  C. 实`.

* Pinyin Input Translation: A full English sentence is shown; the student must type the entire Chinese equivalent using their pinyin keyboard.

* Dialogue Completion: A two-person script where the student must type the response based on social context.

