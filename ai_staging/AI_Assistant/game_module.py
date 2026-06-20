import random
import json
import requests

class GameModule:
    def __init__(self, tts, stt):
        self.tts = tts  # Text-to-speech engine
        self.listen = stt  # Speech-to-text listener
        self.score = 0
        self.high_score = self.load_high_score()

    # ------------------------------
    # High Score Handling
    # ------------------------------
    def load_high_score(self):
        """Load high score from file"""
        try:
            with open("high_score.json", "r") as f:
                return json.load(f).get("high_score", 0)
        except:
            return 0

    def save_high_score(self):
        """Save high score to file"""
        with open("high_score.json", "w") as f:
            json.dump({"high_score": self.high_score}, f)

    # ------------------------------
    # Game Start
    # ------------------------------
    def start_game(self):
        """Game selection via voice"""
        games = {
            "1": "Number Guessing",
            "2": "Riddle Challenge", 
            "3": "Word Quiz",
            "4": "Online Trivia",
            "5": "Math Challenge"
        }

        self.tts.speak("Choose a game: Number guessing, Riddle challenge, Word quiz, Online trivia, or Math challenge.")
        choice = self.listen().lower()

        if "number" in choice or "1" in choice:
            self.enhanced_number_guessing()
        elif "riddle" in choice or "2" in choice:
            self.riddle_game()
        elif "word" in choice or "3" in choice:
            self.word_quiz()
        elif "online" in choice or "4" in choice:
            self.play_online_quiz()
        elif "math" in choice or "5" in choice:
            self.math_challenge()
        else:
            self.tts.speak("Let's play number guessing!")
            self.enhanced_number_guessing()

        # Update score at the end of each round
        self.update_high_score()

    # ------------------------------
    # Game Implementations
    # ------------------------------
    def math_challenge(self):
        """Simple math game"""
        operations = [
            ("+", lambda a, b: a + b),
            ("-", lambda a, b: a - b),
            ("*", lambda a, b: a * b)
        ]
        
        op_symbol, op_func = random.choice(operations)
        a, b = random.randint(1, 10), random.randint(1, 10)
        correct = op_func(a, b)
        
        self.tts.speak(f"What is {a} {op_symbol} {b}?")
        
        try:
            answer = int(self.listen())
            if answer == correct:
                self.tts.speak("Correct! Well done!")
                self.score += 5
            else:
                self.tts.speak(f"Wrong! The correct answer was {correct}.")
        except:
            self.tts.speak("Please say a number.")

    def enhanced_number_guessing(self):
        """Improved number guessing game"""
        self.tts.speak("Choose difficulty: easy (1 to 10), medium (1 to 50), or hard (1 to 100)?")
        level = self.listen().lower()
        
        ranges = {"easy": 10, "medium": 50, "hard": 100}
        max_num = ranges.get(level, 20)
        number = random.randint(1, max_num)
        
        self.tts.speak(f"Guess a number between 1 and {max_num}")

        for attempt in range(5):
            try:
                guess = int(self.listen())
                if guess == number:
                    self.tts.speak("Congratulations! You got it!")
                    self.score += max_num // 10
                    break
                elif guess < number:
                    self.tts.speak("Go higher!")
                else:
                    self.tts.speak("Go lower!")
            except:
                self.tts.speak("Please say a valid number.")
        else:
            self.tts.speak(f"Game over! The number was {number}.")

    def riddle_game(self):
        """Riddle-based challenge"""
        riddles = {
            "What has keys but can’t open locks?": "keyboard",
            "What has hands but can’t clap?": "clock",
            "What has to be broken before you can use it?": "egg"
        }
        question, answer = random.choice(list(riddles.items()))
        self.tts.speak(question)
        user_answer = self.listen().lower()
        if answer in user_answer:
            self.tts.speak("Correct! You’re clever!")
            self.score += 5
        else:
            self.tts.speak(f"Oops! The answer was {answer}.")

    def word_quiz(self):
        """Simple word quiz"""
        words = {
            "A synonym for quick": "fast",
            "Opposite of cold": "hot",
            "Plural of child": "children"
        }
        question, answer = random.choice(list(words.items()))
        self.tts.speak(question)
        user_answer = self.listen().lower()
        if answer in user_answer:
            self.tts.speak("Right answer!")
            self.score += 3
        else:
            self.tts.speak(f"Nope! The correct answer was {answer}.")

    def play_online_quiz(self):
        """Trivia from OpenTDB API"""
        try:
            url = "https://opentdb.com/api.php?amount=1&type=multiple"
            res = requests.get(url).json()
            question = res['results'][0]['question']
            correct = res['results'][0]['correct_answer'].lower()
            self.tts.speak(question)
            answer = self.listen().lower()
            if correct in answer:
                self.tts.speak("Nice! That’s correct!")
                self.score += 10
            else:
                self.tts.speak(f"Wrong! The correct answer was {correct}.")
        except:
            self.tts.speak("Couldn’t connect to the online quiz server.")

    # ------------------------------
    # Utility Functions
    # ------------------------------
    def update_high_score(self):
        """Check and update high score"""
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
            self.tts.speak(f"New high score! {self.score} points!")

    def get_game_stats(self):
        """Return current game statistics"""
        return {
            "current_score": self.score,
            "high_score": self.high_score
        }

    def reset_game(self):
        """Reset current game"""
        self.score = 0
        self.tts.speak("Game reset!")

# ------------------------------
# Android-Specific Subclass
# ------------------------------
class AndroidGameModule(GameModule):
    def __init__(self, tts, stt, android_context):
        super().__init__(tts, stt)
        self.android_context = android_context
        
    def show_game_screen(self):
        """Switch to game UI screen in Android app"""
        # (To be implemented when building Android interface)
        pass
        
    def vibrate_feedback(self, duration=100):
        """Provide haptic feedback on Android"""
        try:
            from jnius import autoclass
            Context = autoclass('android.content.Context')
            VibrationEffect = autoclass('android.os.VibrationEffect')
            vibrator = self.android_context.getSystemService(Context.VIBRATOR_SERVICE)
            effect = VibrationEffect.createOneShot(duration, VibrationEffect.DEFAULT_AMPLITUDE)
            vibrator.vibrate(effect)
        except Exception as e:
            print("Vibration not supported:", e)
